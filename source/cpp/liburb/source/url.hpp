/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#ifndef __ZOOKEEPER_URL_HPP__
#define __ZOOKEEPER_URL_HPP__

#include <string>

#include <stout/error.hpp>
#include <stout/option.hpp>
#include <stout/strings.hpp>
#include <stout/try.hpp>

namespace liburb {

// Describes a ZooKeeper URL of the form:
//
//     urb://username:password@servers
//
// Where username:password is for the message broker
// and servers
// is of the form:
//
//     host1:port1,host2:port2,host3:port3
//
class URL
{
public:
    static Try<URL> parse(const std::string& url);

    const std::string servers;
    const std::string credentials;
    const std::string path;
    const bool ha;

private:
    URL(const std::string& _servers,
        const std::string& _path,
        const bool _ha)
        : servers(_servers),
          path(_path),
          ha(_ha) {}

    URL(const std::string& _credentials,
        const std::string& _servers,
        const std::string& _path,
        const bool _ha)
        : servers(_servers),
          credentials(_credentials),
          path(_path),
          ha(_ha) {}
};


inline Try<URL> URL::parse(const std::string& url)
{
    std::string s = strings::trim(url);
    bool ha = false;

    size_t index = s.find("urb://");

    if (index != 0) {
        return Error("Expecting 'urb://' at the beginning of the URL");
    }

    // Trim off the 'urb://'
    s = s.substr(6);

    //Now look for 'ha://' to see if this is a ha configuration
    index = s.find("ha://");

    if( index == 0) {
        // Trim off the 'ha://'
        s = s.substr(5);
        ha = true;
    } else {
        // We don't support multiple servers if ha is not enabled
        index = s.find_first_of(",");
        if(index != std::string::npos) {
            return Error("Expecting a single server when HA is not specified");
        }
    }

    // Look for the trailing '/' (if any), that's where the path starts.
    std::string path;
    do {
        index = s.find_last_of('/');

        if (index == std::string::npos) {
            break;
        } else {
            path = s.substr(index) + path;
            s = s.substr(0, index);
        }
    } while (true);

    if (path == "") {
        path = "/";
    }

    // Look for the trailing '@' (if any), that's where servers starts.
    index = s.find_last_of('@');

    if (index != std::string::npos) {
        return URL(s.substr(0, index), s.substr(index + 1), path, ha);
    } else {
        return URL(s, path, ha);
    }
}

inline std::ostream& operator << (std::ostream& stream, const URL& url)
{
    stream << "urb://";
    if (!url.credentials.empty()) {
        stream << url.credentials << "@";
    }
    return stream << url.servers << url.path;
}

} // namespace liburb {

#endif // __URL_HPP__
