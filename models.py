"""
Recommendation Model
You must initlaize this class before use by calling inititlize().
"""

import os
import json
import logging
import pickle
from requests import HTTPError, ConnectionError
from cloudant.client import Cloudant
from cloudant.query import Query

class DataValidationError(Exception):
    """ Custom Exception with data validation fails """
    pass

class Recommendation(object):
    """ Recommendation interface to database """
    logger = logging.getLogger(__name__)
    client = None
    database = None

    def __init__(self, productId=None, suggestionId=None, categoryId=None):
        """ Constructor """
        self.id = None
        self.productId = productId
        self.suggestionId = suggestionId
        self.categoryId = categoryId

    def save(self):
        if self.productId is None:   # productId is the only required field
            raise DataValidationError('productId attribute is not set')
        if self.id:
            self.update()
        else:
            self.create()

    def create(self):
        if self.productId is None:   # productId is the only required field
            raise DataValidationError('name attribute is not set')

        try:
            document = self.database.create_document(self.serialize())
        except HTTPError as err:
            Recommendation.logger.warning('Create failed: %s', err)
            return

        if document.exists():
            self.id = document['_id']

    def delete(self):
        try:
            document = self.database[self.id]
        except KeyError:
            document = None
            Recommendation.logger.info('Unable to delete Recommendation with id %s', self.id)
        if document:
            document.delete()

    def update(self): 
        try:
            document = self.database[self.id]
        except KeyError:
            document = None
            Recommendation.logger.info('Unable to locate Recommendation with id %s for update', self.id)
        if document:
            document.update(self.serialize())
            document.save()

    def serialize(self):
        """ Serializes a Recommendation into a dictionary """
        recommendation = {
            "productId": self.productId, 
            "suggestionId": self.suggestionId, 
            "categoryId": self.categoryId
        }
        if self.id:
            recommendation['_id'] = self.id
        return recommendation

    def deserialize(self, data):
        """
        Deserializes a Recommendation from a dictionary
        Args:
            data (dict): A dictionary containing the Recommendation data
        """
        Recommendation.logger.info(data)
        try:
            self.productId = data['productId']
            self.suggestionId = data['suggestionId']
            self.categoryId = data['categoryId']
        except KeyError as error:
            raise DataValidationError('Invalid recommendation: missing ' + error.args[0])
        except TypeError as error:
            raise DataValidationError('Invalid recommendation: body of request contained bad or no data')
        # if there is no id and the data has one, assign it
        if not self.id and '_id' in data:
            self.id = data['_id']

        return self

######################################################################
#  S T A T I C   D A T A B S E   M E T H O D S
######################################################################

    @classmethod
    def connect(cls):
        """ Connect to the server """
        cls.client.connect()

    @classmethod
    def disconnect(cls):
        """ Disconnect from the server """
        cls.client.disconnect()

    @classmethod
    def remove_all(cls):
        for document in cls.database:
            document.delete()


    @classmethod
    def all(cls):
        """ Query that returns all recommendations """
        results = []
        for doc in cls.database:
            recommendation = Recommendation().deserialize(doc)
            recommendation.id = doc['_id']
            results.append(recommendation)
        return results


    @classmethod
    def find(cls, targetId): 
        """ Query that finds Recommendation by their id """
        try:
            document = cls.database[targetId]
            return Recommendation().deserialize(document)
        except KeyError:
            return None

    @classmethod
    def find_by(cls, **kwargs):
        """ Find records using selector """
        query = Query(cls.database, selector=kwargs)
        results = []
        for doc in query.result:
            recommendation = Recommendation()
            recommendation.deserialize(doc)
            results.append(recommendation)
        return results

    @classmethod
    def find_by_productId(cls, productId):
        """ Query that finds Recommendations by their productId """
        return cls.find_by(productId=productId)

    @classmethod
    def find_by_categoryId(cls, categoryId):
        """ Query that finds Recommendations by their categoryId """
        return cls.find_by(categoryId=categoryId)

    @classmethod
    def find_by_suggestionId(cls, suggestionId):
        """ Query that finds Recommendations by their suggestionId """
        return cls.find_by(suggestionId=suggestionId)


############################################################
#  C L O U D A N T   D A T A B A S E   C O N N E C T I O N
############################################################
    @staticmethod
    def init_db(dbname='recommendations'):
        """
        Initialized Coundant database connection
        """
        opts = {}
        vcap_services = {}
        # Try and get VCAP from the environment or a file if developing
        if 'VCAP_SERVICES' in os.environ:
            Recommendation.logger.info('Running in Bluemix mode.')
            vcap_services = json.loads(os.environ['VCAP_SERVICES'])
        # if VCAP_SERVICES isn't found, maybe we are running on Kubernetes?
        elif 'BINDING_CLOUDANT' in os.environ:
            Recommendation.logger.info('Found Kubernetes Bindings')
            creds = json.loads(os.environ['BINDING_CLOUDANT'])
            vcap_services = {"cloudantNoSQLDB": [{"credentials": creds}]}
        else:
            Recommendation.logger.info('VCAP_SERVICES and BINDING_CLOUDANT undefined.')
            # creds = {
            #     "host": '127.0.0.1',
            #     "port": 5984,
            #     "url": "http://127.0.0.1:5984/"
            # }
            creds = {
                "username": "admin",
                "password": "pass",
                "host": '127.0.0.1',
                "port": 5984,
                "url": "http://admin:pass@127.0.0.1:5984/"
            }
            vcap_services = {"cloudantNoSQLDB": [{"credentials": creds}]}

        # Look for Cloudant in VCAP_SERVICES
        for service in vcap_services:
            if service.startswith('cloudantNoSQLDB'):
                cloudant_service = vcap_services[service][0]
                opts['username'] = cloudant_service['credentials']['username']
                opts['password'] = cloudant_service['credentials']['password']
                opts['host'] = cloudant_service['credentials']['host']
                opts['port'] = cloudant_service['credentials']['port']
                opts['url'] = cloudant_service['credentials']['url']

        # if any(k not in opts for k in ('host', 'port', 'url')):
        #     Recommendation.logger.info('Error - Failed to retrieve options. ' \
        #                      'Check that app is bound to a Cloudant service.')
        #     exit(-1)
        if any(k not in opts for k in ('host', 'username', 'password', 'port', 'url')):
            Recommendation.logger.info('Error - Failed to retrieve options. ' \
                             'Check that app is bound to a Cloudant service.')
            exit(-1)

        Recommendation.logger.info('Cloudant Endpoint: %s', opts['url'])
        try:
            # Recommendation.client = Cloudant(
            #                       url=opts['url'],
            #                       connect=True,
            #                       auto_renew=True
            #                      )
            Recommendation.client = Cloudant(opts['username'],
                                  opts['password'],
                                  url=opts['url'],
                                  connect=True,
                                  auto_renew=True
                                 )
        except ConnectionError:
            raise AssertionError('Cloudant service could not be reached')

        # Create database if it doesn't exist
        try:
            Recommendation.database = Recommendation.client[dbname]
        except KeyError:
            # Create a database using an initialized client
            Recommendation.database = Recommendation.client.create_database(dbname)
        # check for success
        if not Recommendation.database.exists():
            raise AssertionError('Database [{}] could not be obtained'.format(dbname))