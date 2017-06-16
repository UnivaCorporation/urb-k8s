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



from urb.config.config_manager import ConfigManager
from urb.log.log_manager import LogManager
from urb.exceptions.configuration_error import ConfigurationError
from urb.db.framework_db_interface import FrameworkDBInterface
from urb.db.event_db_interface import EventDBInterface

class DBManager(object):

    # Singleton.
    __instance = None

    def __new__(cls, *args, **kwargs):
        # Allow subclasses to create their own instances.
        if cls.__instance is None or cls != type(cls.__instance):
            instance = object.__new__(cls, *args, **kwargs)
            instance.__init__()
            cls.__instance = instance
        return cls.__instance

    @classmethod
    def get_instance(cls, *args, **kwargs):
        return cls.__new__(cls, *args, **kwargs)

    def __init__(self):
        """ Initialize factory instance. """
        # Only initialize once.
        if DBManager.__instance is not None:
            return
        self.logger = LogManager.get_instance().get_logger(
            self.__class__.__name__)
        self.db_client = None
            
    def __create_db_client(self):
        """ Create db client. """
        self.logger.debug('Creating db client')
        cm = ConfigManager.get_instance()
        db_client_config = cm.get_config_option('DBManager', 'db_client')
            
        if db_client_config is None:
            self.logger.error(
                'db_client parameter missing from config file: %s' 
                % (cm.get_config_file()))
            return
        try:
            dot_pos = db_client_config.find('.')
            self.db_client_module = db_client_config[0:dot_pos]
            self.db_client_constructor = db_client_config[dot_pos+1:]
            self.db_client_class = \
                self.db_client_constructor.split('(')[0]
            exec 'from %s import %s' % (self.db_client_module,
                self.db_client_class)
            cmd = 'db_client = %s' % self.db_client_constructor
            self.logger.debug('Using %s' % cmd)
            exec cmd
            return db_client
        except Exception, ex:
            self.logger.warn('Could not create db client: %s' % ex)
        return None

    def get_db_client(self):
        """ Get db_client. """
        if self.db_client is None:
            self.db_client = self.__create_db_client()
        return self.db_client

    def get_framework_db_interface(self):
        db_client = self.get_db_client()
        if db_client is None:
            return None
        return FrameworkDBInterface(db_client)

    def get_event_db_interface(self):
        db_client = self.get_db_client()
        if db_client is None:
            return None
        return EventDBInterface(db_client)

# Testing
if __name__ == '__main__':
    mgr = DBManager.get_instance()
    print mgr
    print mgr.get_db_client()

