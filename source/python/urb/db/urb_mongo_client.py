#!/usr/bin/env python
# ___INFO__MARK_BEGIN__
# ############################################################################
#
# This code is the Property, a Trade Secret and the Confidential Information
#  of Univa Corporation.
#
#  Copyright Univa Corporation. All Rights Reserved. Access is Restricted.
#
#  It is provided to you under the terms of the
#  Univa Term Software License Agreement.
#
#  If you have any questions, please contact our Support Department.
#
#  www.univa.com
#
###########################################################################
#___INFO__MARK_END__


from pymongo import MongoClient
from urb.log.log_manager import LogManager
from urb.exceptions.db_error import DBError

class URBMongoClient(object):
    """Class responsible for interaction with MongoDB."""

    driver = None

    DB_NAME = 'urb'
    # clean old data after number of specified months (0 - never expire)
    TTL_MONTHS = 0

    def __init__(self, db_uri='mongodb://localhost:27017/', db_name=DB_NAME, expire=TTL_MONTHS):
        self.logger = LogManager.get_instance().get_logger(self.__class__.__name__)
        try:
            self.client = MongoClient(db_uri,use_greenlets=True)
            self.db = self.client[db_name]
            self.expire = expire
        except Exception, ex:
            self.logger.warn('Cannot connect to Mongo DB: %s' % ex)
            raise DBError(exception=ex)

    def drop(self, collection):
        return self.db[collection].drop()

    def insert(self, collection, dict, **kwargs):
        return self.db[collection].insert(dict, **kwargs)
    
    def update(self, collection, query, update, **kwargs):
        key = '.'.join((collection, str(update['$set'].keys()[0])))
        return self.db[collection].update(query, update, **kwargs)

    def find_one(self, collection, criteria={}):
        return self.db[collection].find_one(criteria)

    def find(self, collection, criteria={}, projections={}):
        return self.db[collection].find(criteria, projections)

    def find_as_list(self, collection, criteria={}, projections={}):
        return list(self.db[collection].find(criteria, projections))

    def collection_names(self):
        return self.db.collection_names()

    def create_ttl_index(self, collection, key, seconds):
        return self.db[collection].create_index(key, name="ttl_index", expireAfterSeconds=seconds)

    def drop_ttl_index(self, collection):
        return self.db[collection].drop_index("ttl_index")

    def get_index_information(self, collection):
        return self.db[collection].index_information()

# Testing
if __name__ == '__main__':
    mongo = URBMongoClient()

    mongo.drop('students')
    id = mongo.insert('students', { '_id' : 1, 'semester' : 1, 'grades' : [ 70, 87, 90 ]   })
    print 'Student #1 id: ', id
    id = mongo.insert('students', { '_id' : 2, 'semester' : 1, 'grades' : [ 90, 88, 92 ] } )
    print 'Student #2 id: ', id
    print mongo.find_as_list('students', criteria={ 'semester' : 1, 'grades': { '$gte' : 85 } }, projections={ 'grades.$' : 1 } )

    result = mongo.update('frameworks', {'_id' : 2}, {'$set' : {'task_id' : 2}}, upsert=True)
    print result

    doc = mongo.find_one('frameworks', {'task_id' : 1})
    print doc
    docs = mongo.find('frameworks', projections={'task_id' : 1})
    print docs.count()
    docs = mongo.find_as_list('frameworks', projections={'task_id' : 1})
    print docs
    print 'Collection names: ', mongo.collection_names()
    mongo.drop('students')
    print 'Collection names (after drop): ', mongo.collection_names()
