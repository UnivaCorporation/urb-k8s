// Copyright (c) 2014 Luca Marturana. All rights reserved.
// Licensed under Apache 2.0, see LICENSE for details

#pragma once

#include <string>
#include <redis3m/utils/exception.h>
#include <redis3m/utils/noncopyable.h>
#include <redis3m/connection.h>
#include <redis3m/reply.h>
#include <ev.h>
#include <vector>
#include <mutex>
#include <memory>


struct redisAsyncContext;

namespace redis3m {

class async_callback {
   public:
     async_callback() {};
     ~async_callback() {};
      virtual void onReply(redisAsyncContext *, redis3m::reply&) {};
      static void callback(redisAsyncContext *c, void *vr, void *privdata);
};

/**
* @brief The connection class, represent a connection to a Redis server
*/
class async_connection: utils::noncopyable
{
public:
    typedef std::shared_ptr<async_connection> ptr_t;

    /**
     * @brief Create and open a new connection
     * @param host hostname or ip of redis server, default localhost
     * @param port port of redis server, default: 6379
     * @return
     */
    inline static ptr_t create(const std::string& host="localhost",
                               const int port=6379, struct ev_loop* loop=ev_default_loop())
    {
        return ptr_t(new async_connection(host, port, loop));
    }

    ~async_connection();

    void disconnect();

    bool is_valid() const;

    /**
     * @brief Queue an async command at Redis server
     * @param args vector with args, example [ "SET", "foo", "bar" ]
     */
     void execute(const std::vector<std::string> &commands, std::shared_ptr<async_callback> callback);


    /**
     * @brief Get a reply from server, blocking call if no reply is ready
     * @return reply object
     */
    reply get_reply();

    /**
     * @brief Get specific count of replies requested, blocking if they
     * are not ready yet.
     * @param count
     * @return
     */
    std::vector<reply> get_replies(unsigned int count);

    /**
     * @brief Returns raw ptr to hiredis library connection.
     * Use it with caution and pay attention on memory
     * management.
     * @return
     */
    inline redisAsyncContext* c_ptr() { return c; }

    enum role_t {
        ANY = 0,
        MASTER = 1,
        SLAVE = 2
    };

private:
    friend class async_connection_pool;
    async_connection(const std::string& host, const int port,struct ev_loop* loop);

    role_t _role;
    redisAsyncContext *c;
    std::mutex access_mutex;
};
}
