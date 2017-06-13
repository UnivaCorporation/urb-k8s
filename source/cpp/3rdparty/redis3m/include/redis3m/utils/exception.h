// Copyright (c) 2014 Luca Marturana. All rights reserved.
// Licensed under Apache 2.0, see LICENSE for details

#pragma once

#include <stdexcept>
#include <string>
#include <utility>

namespace redis3m {
    class exception: public std::runtime_error
    {
    public:
        explicit exception(const std::string& what) : std::runtime_error(what) {}
        explicit exception(const char *what) : std::runtime_error(what) {}
        virtual ~exception() = default;
    };
}

#define REDIS3M_EXCEPTION(name) class name: public redis3m::exception {\
    public: name(const std::string& what="") : exception(std::move(std::string(#name) + ": " + what)) {}\
    public: name(const char *what) : exception(std::move(std::string(#name) + ": " + what)) {}\
};

#define REDIS3M_EXCEPTION_2(name, super) class name: public super {\
    public: name(const std::string& what="") : super(std::move(std::string(#name) + ": " + what)) {}\
    public: name(const char *what) : super(std::move(std::string(#name) + ": " + what)) {}\
};
