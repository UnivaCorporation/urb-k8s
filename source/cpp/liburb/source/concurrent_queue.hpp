
#ifndef _CONCURRENT_QUEUE_HPP
#define _CONCURRENT_QUEUE_HPP

#include <mutex>
#include <queue>

template<typename Data>
class concurrent_queue
{
private:
    std::queue<Data> the_queue;
    mutable std::mutex the_mutex;
public:
    void push(Data const& data)
    {
        std::lock_guard<std::mutex> lock(the_mutex);
        the_queue.push(data);
    }

    bool empty() const
    {
        std::lock_guard<std::mutex> lock(the_mutex);
        return the_queue.empty();
    }

    bool try_pop(Data& popped_value)
    {
        std::lock_guard<std::mutex> lock(the_mutex);
        if(the_queue.empty())
        {
            return false;
        }

        popped_value = the_queue.front();
        the_queue.pop();
        return true;
    }
};

#endif //#ifndef _CONCURRENT_QUEUE_HPP
