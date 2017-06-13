// Copyright (c) 2014 Luca Marturana. All rights reserved.
// Licensed under Apache 2.0, see LICENSE for details

#pragma once

#include <string>
#include <set>
#include <redis3m/async_connection.h>
#include <redis3m/connection.h>
#include <mutex>
#include <memory>
#include <redis3m/utils/exception.h>
#include <redis3m/utils/noncopyable.h>
#include <ev.h>

namespace redis3m {
    /**
     * @brief Manages a connection pool, using a Redis Sentinel
     * to get instances ip, managing also failover
     */
    class async_connection_pool: utils::noncopyable
    {
    public:
        typedef std::shared_ptr<async_connection_pool> ptr_t;

        /**
         * @brief Create a new connection_pool
         * @param sentinel_host Can be a single host or a list separate by commas,
         * if an host has multiple IPs, connection_pool tries all of them
         * @param master_name Master to lookup
         * @param sentinel_port Sentinel port, default 26379
         * @return
         */
        static inline ptr_t create(const std::string& sentinel_host,
                                   const std::string& master_name,
                                   struct ev_loop* loop=ev_default_loop(),
                                   int sentinel_port=26379)
        {
            return ptr_t(new async_connection_pool(sentinel_host, master_name, loop, sentinel_port));
        }

        /**
         * @brief Ask for a connection
         * @return a valid connection object
         */
        async_connection::ptr_t get();

        /**
         * @brief Put a connection again on pool for reuse, pay attention to
         * insert only connection created from the same pool. Otherwise unpexpected
         * behaviours can happen.
         * @param conn
         */
        void put(async_connection::ptr_t conn );

    private:
        async_connection_pool(const std::string& sentinel_host,
                        const std::string& master_name,
                        struct ev_loop* loop,
                        int sentinel_port);
        async_connection::ptr_t create_slave_connection();
        async_connection::ptr_t create_master_connection();
        connection::ptr_t sentinel_connection();
        static async_connection::role_t get_role(async_connection::ptr_t conn);
        std::mutex access_mutex;
        std::set<async_connection::ptr_t> connections;

        std::vector<std::string> sentinel_hosts;
        unsigned int sentinel_port;
        std::string master_name;
        struct ev_loop* loop;
    };
}
