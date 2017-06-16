// Copyright (c) 2014 Luca Marturana. All rights reserved.
// Licensed under Apache 2.0, see LICENSE for details

#include <redis3m/async_connection_pool.h>
#include <redis3m/connection_pool.h>
#include <redis3m/command.h>
#include <redis3m/utils/resolv.h>
#include <redis3m/utils/logging.h>
#include <chrono>
#include <thread>
#include <regex>

using namespace redis3m;

async_connection_pool::async_connection_pool(const std::string& sentinel_host,
                                 const std::string& master_name,
                                 struct ev_loop* loop,
                                 int sentinel_port):
master_name(master_name),
sentinel_port(sentinel_port),
loop(loop)
{
#if 0
    std::regex rgx(",");
    std::sregex_token_iterator first{std::begin(sentinel_host), std::end(sentinel_host), rgx, -1}, last;
    sentinel_hosts = {first, last};
#else
    std::string token;
    std::for_each(std::begin(sentinel_host), std::end(sentinel_host), [&](char c) {
        if (!isspace(c))
        {
            token += c;
        }
        else
        {
            if (token.length()) sentinel_hosts.push_back(token);
            token.clear();
        }
    });
    if (token.length()) sentinel_hosts.push_back(token);
#endif
//    boost::algorithm::split(sentinel_hosts, sentinel_host, boost::is_any_of(","), boost::token_compress_on);
}

async_connection::ptr_t async_connection_pool::get()
{
    async_connection::ptr_t ret;

    // Look for a cached connection
    {
        std::lock_guard<std::mutex> lock(access_mutex);
        std::set<async_connection::ptr_t>::const_iterator it = connections.begin();
        if (it != connections.end())
        {
            ret = *it;
            connections.erase(it);
        }
    }

    // If no connection found, create a new one
    if (!ret)
    {
        ret = create_master_connection();
    }
    return ret;
}

void async_connection_pool::put(async_connection::ptr_t conn)
{
    if (conn->is_valid())
    {
        std::lock_guard<std::mutex> lock(access_mutex);
        connections.insert(conn);
    }
}

connection::ptr_t async_connection_pool::sentinel_connection()
{
    for (const std::string& host: sentinel_hosts)
    {
        // Check if each host has a port
        int real_port = sentinel_port;
        std::string real_host = host;
        size_t index = host.find_first_of(":");
        if( index != std::string::npos ) {
            // We have a port
           real_host = host.substr(0, index);
           try {
               real_port = std::stoi(host.substr(index+1));
               if (real_port < 0) {
                   std::string err("Cannot find sentinel: negative port: ");
                   err += std::to_string(real_port);
                   logging::error(err);
                   throw cannot_find_sentinel(err);
               }
           } catch (const std::exception& ex) {
               std::string err("Cannot find sentinel: invalid port: ");
               err += host.substr(index+1);
               logging::error(err);
               throw cannot_find_sentinel(err);
           }
        }
        std::vector<std::string> real_sentinels = resolv::get_addresses(real_host);
        std::string msg("Found ");
        msg += std::to_string(real_sentinels.size()) + " redis sentinels: " +
                std::accumulate(std::begin(real_sentinels), std::end(real_sentinels), std::string(),
                                [](const std::string& a, const std::string& b) -> std::string {
                                        return a + (a.length() > 0 ? ", " : "") + b;
                                  }) + std::to_string(real_port);
        logging::debug(msg);

        for (const std::string& real_sentinel: real_sentinels)
        {
            std::string msg = "Trying sentinel " + real_sentinel;
            logging::debug(msg);
            try
            {
                return connection::create(real_sentinel, real_port);
            } catch (const unable_to_connect& ex)
            {
                logging::debug(real_sentinel + " is down");
            }
        }
    }
    throw cannot_find_sentinel("Cannot find sentinel");
}

async_connection::role_t async_connection_pool::get_role(async_connection::ptr_t conn)
{
    return async_connection::MASTER;
}

async_connection::ptr_t async_connection_pool::create_slave_connection()
{
    connection::ptr_t sentinel = sentinel_connection();
    sentinel->append(command("SENTINEL") << "slaves" << master_name );
    reply response = sentinel->get_reply();
    std::vector<reply> slaves(response.elements());
    std::random_shuffle(slaves.begin(), slaves.end());

    for (std::vector<reply>::const_iterator it = slaves.begin();
         it != slaves.end(); ++it)
    {
        const std::vector<reply>& properties = it->elements();
        if (properties.at(9).str() == "slave")
        {
            std::string host = properties.at(3).str();
            int port = std::stoi(properties.at(5).str());
            try
            {
                async_connection::ptr_t conn = async_connection::create(host, port, loop);
                async_connection::role_t role = get_role(conn);
                if (role == async_connection::SLAVE)
                {
                    conn->_role = role;
                    return conn;
                }
                else
                {
                    std::string msg = "Error on connection to " + host + ":" + std::to_string(port) +
                                      " declared to be slave but it's not, waiting";
                    logging::debug(msg);
                }
            } catch (const unable_to_connect& ex)
            {
                std::string msg = "Error on connection to Slave " + host + ":" + std::to_string(port) +
                                  " declared to be up";
                logging::debug(msg);
            }
        }
    }
    throw cannot_find_slave();
}

async_connection::ptr_t async_connection_pool::create_master_connection()
{
    unsigned int connection_retries = 0;
    while (connection_retries < 20)
    {
        connection::ptr_t sentinel = sentinel_connection();
        reply masters = sentinel->run(command("SENTINEL") << "masters" );
        for (const reply& master: masters.elements())
        {
            if (master.elements().at(1).str() == master_name)
            {
                const std::string& flags = master.elements().at(9).str();
                if (flags == "master")
                {
                    const std::string& master_ip = master.elements().at(3).str();
                    int master_port = std::stoi(master.elements().at(5).str());

                    try
                    {
                        async_connection::ptr_t conn = async_connection::create(master_ip, master_port, loop);
                        async_connection::role_t role = get_role(conn);
                        if (role == async_connection::MASTER)
                        {
                            conn->_role = role;
                            return conn;
                        }
                        else
                        {
                            std::string msg = "Error on connection to " + master_ip + ":" + std::to_string(master_port) +
                                              " declared to be master but it's not, waiting";
                            logging::debug(msg);
                        }
                    } catch (const unable_to_connect& ex)
                    {
                        std::string msg = "Error on connection to Master " + master_ip + ":" +
                                          std::to_string(master_port) + " declared to be up, waiting";
                        logging::debug(msg);
                    }
                }
            }
        }
        connection_retries++;
        std::this_thread::sleep_for(std::chrono::seconds(5));
    }
    std::string msg = "Unable to find master of name: " + master_name + " (too many retries)";
    throw cannot_find_master(msg);
}
