// Copyright (c) 2014 Luca Marturana. All rights reserved.
// Licensed under Apache 2.0, see LICENSE for details

#include <redis3m/async_connection.h>
#include <hiredis.h>
#include <async.h>
#include <adapters/libev.h>
#include <cassert>
#include <iostream>

using namespace redis3m;

async_connection::async_connection(const std::string& host, const int port, struct ev_loop* loop)
{
    c = redisAsyncConnect(host.c_str(), port);
    redisContext *ctx = &(c->c);
    if (c->err != REDIS_OK)
    {
        redisAsyncFree(c);
        std::string err = "unable to connect to " + host + ":" + std::to_string(port);
        throw unable_to_connect(err);
    }
    // Hook up to the event loop...
    redisLibevAttach(loop, c);
}

void async_connection::disconnect() {
    //Only disconnect if we haven't yet...
    redisContext *ctx = &(c->c);
    if( ! (ctx->flags & REDIS_FREEING) && ! (ctx->flags & REDIS_DISCONNECTING) ) {
       redisAsyncDisconnect(c);
    }
    c = NULL;
}

async_connection::~async_connection()
{
    std::lock_guard<std::mutex> l(access_mutex);
    if(c != NULL) {
        disconnect();
    }
}


void async_connection::execute(const std::vector<std::string> &commands, std::shared_ptr<async_callback> callback)
{
    int ret = 0;//redisAppendCommandArgv(c, static_cast<int>(commands.size()), argv.data(), argvlen.data());
    std::vector<const char*> argv;
    argv.reserve(commands.size());
    std::vector<size_t> argvlen;
    argvlen.reserve(commands.size());

    for (std::vector<std::string>::const_iterator it = commands.begin(); it != commands.end(); ++it) {
        argv.push_back(it->c_str());
        argvlen.push_back(it->size());
    }
    {
        std::lock_guard<std::mutex> lock(access_mutex);
        if (!is_valid()) {
            std::string err = "async_connection::execute: async_connection is not valid: redisAsyncContext ptr=" +
                              std::to_string(reinterpret_cast<uintptr_t>(c)) + ", redis status=" + std::to_string(c->err);
            throw transport_failure(err);
        }

        std::shared_ptr<async_callback> *pCb = new std::shared_ptr<async_callback>();
        *pCb = callback;

        ret = redisAsyncCommandArgv(c, (*pCb)->callback, pCb, static_cast<int>(commands.size()), argv.data(), argvlen.data());
    }
    if (ret != REDIS_OK)
    {
        std::string err = "async_connection::execute: redisAsyncCommandArgv returned redis status=" + std::to_string(c->err);
        throw transport_failure(err);
    }
}

reply async_connection::get_reply()
{
    static const std::string strReadOnly("READONLY");
    static const size_t len = strReadOnly.size();
    redisReply *r;
    int error = 0; //redisGetReply(c, reinterpret_cast<void**>(&r));
    if (error != REDIS_OK)
    {
        throw transport_failure("async_connection::get_reply");
    }
    reply ret(r);
    freeReplyObject(r);

    if (ret.type() == reply::type_t::ERROR &&
        !ret.str().compare(0, len, strReadOnly))
    {
        throw slave_read_only("async_connection::get_reply");
    }
    return ret;
}

std::vector<reply> async_connection::get_replies(unsigned int count)
{
    std::vector<reply> ret;
    for (int i=0; i < count; ++i)
    {
        ret.push_back(get_reply());
    }
    return ret;
}

bool async_connection::is_valid() const
{
    return c != NULL && c->err == REDIS_OK;
}

void async_callback::callback(redisAsyncContext *c, void *vr, void *privdata) {
    assert( privdata != NULL);
    assert( c != NULL);
    std::shared_ptr<async_callback> *pCb = static_cast<std::shared_ptr<async_callback>*>(privdata);
    if( vr != NULL) {
        redisReply *r = reinterpret_cast<redisReply*>(vr);
        reply ret(r);
        (*pCb)->onReply(c,ret);
    } else {
        //Null... return a NIL
        reply ret;
        (*pCb)->onReply(c,ret);
    }
    // Always need to delete the allocated cb
    delete pCb;
}
