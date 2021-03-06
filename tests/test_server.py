"""
Pet API Service Test Suite
Test cases can be run with the following:
nosetests
"""

import unittest
import logging
import json
import os
from flask import abort, request
from time import sleep # use for rate limiting Cloudant Lite :(
from werkzeug.datastructures import MultiDict, ImmutableMultiDict

from flask_api import status    # HTTP Status Codes
from service.models import Recommendation, DataValidationError
from service import app

# import unittest
# import json
# from werkzeug.datastructures import MultiDict, ImmutableMultiDict
# from service import app
# from service.models import Pet

# Status Codes
HTTP_200_OK = 200
HTTP_201_CREATED = 201
HTTP_204_NO_CONTENT = 204
HTTP_400_BAD_REQUEST = 400
HTTP_404_NOT_FOUND = 404
HTTP_405_METHOD_NOT_ALLOWED = 405
HTTP_409_CONFLICT = 409

######################################################################
#  T E S T   C A S E S
######################################################################
class TestRecommendationService(unittest.TestCase):
    """ Recommendation Service tests """

    logger = logging.getLogger(__name__)

    def setUp(self):
        """Runs before each test"""
        self.app = app.test_client()
        Recommendation.init_db("tests")
        sleep(0.5)
        Recommendation.remove_all()
        sleep(0.5)
        Recommendation(id=1, productId='Infinity Gauntlet', suggestionId='Soul Stone', categoryId='Comics').save()
        sleep(0.5)
        Recommendation(id=2, productId='iPhone', suggestionId='iphone Case', categoryId='Electronics').save()
        sleep(0.5)

    def tearDown(self):
        """Runs towards the end of each test"""
        Recommendation.remove_all()


    def tearDown(self):
        """Runs towards the end of each test"""
        Recommendation.remove_all()

    def test_index(self):
        resp = self.app.get('/')
        self.assertEqual(resp.status_code, HTTP_200_OK)
        self.assertIn('', resp.data)

    def test_get_recommendation(self):
        # self.assertEqual(self.get_recommendation_count(), 2)
        recommendation = self.get_recommendation('iPhone')[0]
        resp = self.app.get('/recommendations/2')
        self.assertEqual(resp.status_code, HTTP_200_OK)
        data = json.loads(resp.data)
        self.assertEqual(data['suggestionId'], 'iphone Case')

    def test_get_nonexisting_recommendation(self):
        resp = self.app.get('/recommendations/{}'.format("abc"))
        self.assertEqual(resp.status_code, HTTP_404_NOT_FOUND)

    def test_create_recommendation(self):
        new_recommenation = dict(id=3, productId='Table', suggestionId='Chair', categoryId='Home Appliances')
        data = json.dumps(new_recommenation)
        resp = self.app.post('/recommendations', data=data, content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

         # Make sure location header is set
        location = resp.headers.get('Location', None)
        self.assertNotEqual(location, None)

    def test_create_recommendation_bad_content_type_format(self):
        new_recommenation = dict(id=3, productId='Table', suggestionId='Chair', categoryId='Home Appliances')
        data = json.dumps(new_recommenation)
        resp = self.app.post('/recommendations', data=data, content_type='application/XML')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_recommendation_no_content_type(self):
        new_recommedation = {'categoryId': 'Sports'}
        data = json.dumps(new_recommedation)
        resp = self.app.post('/recommendations', data=data)
        self.assertEqual(resp.status_code, HTTP_400_BAD_REQUEST)

    #def test_create_recommendation_no_content_type(self):
    #    recommendation = Recommendation(0)
    #    self.assertRaises(DataValidationError, recommendation.deserialize, None)



    def test_call_recommendation_with_an_id(self):
        new_reco = {'productId': 'Car', 'categoryId': 'Automobile'}
        data = json.dumps(new_reco)
        resp = self.app.post('/recommendations/7', data=data)
        self.assertEqual(resp.status_code, HTTP_405_METHOD_NOT_ALLOWED)

    def test_list_all_recommendations(self):
        resp = self.app.get('/recommendations')
        self.assertEqual(resp.status_code, HTTP_200_OK)
        data = json.loads(resp.data)
        self.assertEqual(len(data), 2)

    def test_update_recommendation(self):
        recommendation = self.get_recommendation('iPhone')[0]
        new_recommedation = dict(productId='iPhone', suggestionId='iphone pop ups', categoryId='Electronics')
        data = json.dumps(new_recommedation)
        resp = self.app.put('/recommendations/2', data=data, content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        new_json = json.loads(resp.data)
        self.assertEqual(new_json['suggestionId'], 'iphone pop ups')

    def test_update_recommendation_not_found(self):
        new_reco = dict(id=3,productId='samsung', suggestionId='samsung pop ups', categoryId='Electronocs')
        data = json.dumps(new_reco)
        invalidId = "123"
        recommendation = self.get_recommendation('iPhone')[0]
        resp = self.app.put('/recommendations/{}'.format(invalidId), data=data, content_type='application/json')
        self.assertEqual(resp.status_code, HTTP_404_NOT_FOUND)

    def test_query_recommendation_by_productId(self):
        resp = self.app.get('/recommendations', query_string='productId=iPhone')
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(data), 1)
        self.assertIn('iphone Case', resp.data)
        self.assertNotIn('Infinity Gauntlet', resp.data)
        data = json.loads(resp.data)
        query_item = data[0]
        self.assertEqual(query_item['categoryId'], 'Electronics')

    def test_query_recommendation_by_categoryId(self):
        resp = self.app.get('/recommendations', query_string='categoryId=Electronics')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreater(len(resp.data), 0)
        self.assertIn('iphone Case', resp.data)
        self.assertNotIn('Infinity Gauntlet', resp.data)
        data = json.loads(resp.data)
        query_item = data[0]
        self.assertEqual(query_item['categoryId'], 'Electronics')

    def test_query_recommendation_by_suggestionId(self):
        resp = self.app.get('/recommendations', query_string='suggestionId=iphone Case')
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(data), 1)
        self.assertIn('iphone Case', resp.data)
        self.assertNotIn('Infinity Gauntlet', resp.data)
        data = json.loads(resp.data)
        query_item = data[0]
        self.assertEqual(query_item['categoryId'], 'Electronics')

    def test_delete_recommendation(self):
        # save the current number of recommendations for later comparrison
        recommendation_count = self.get_recommendation_count()
        # delete a recommendation
        recommendation = self.get_recommendation('iPhone')[0]
        resp = self.app.delete('/recommendations/2', content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(resp.data), 0)
        new_count = self.get_recommendation_count()
        self.assertEqual(new_count, recommendation_count - 1)

    def test_delete_all_recommendations(self):
        recommendation_count = self.get_recommendation_count()
        resp = self.app.delete('/recommendations/reset', content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(resp.data), 0)
        new_count = self.get_recommendation_count()
        self.assertEqual(new_count, 0)
        self.assertNotEqual(new_count, recommendation_count)


    def test_update_recommendationCategory(self):
         new_category = { 'categoryId': 'vehilceInsurance'}
         data = json.dumps(new_category)
         resp = self.app.put('/recommendations/category/Electronics', data=data, content_type='application/json')
         self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_update_recommendationCategory_not_found(self):
         dataToUpdate = dict(categoryId='vehicleInsurance')
         resp = self.app.put('/recommendations/category/Mechanics', data=dataToUpdate, content_type='application/json')
         self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)



#class TestResetRecommendations(unittest.TestCase):
#    def test_delete_all_recommendations(self):
#       recommendation = Recommendation.all()
#        resp = self.app.delete('/recommendations', content_type='application/json')
#        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        #self.assertEqual(len(resp.data), 0)


######################################################################
# Utility functions
######################################################################
    def get_recommendation(self, productId):
        """ retrieves a pet for use in other actions """
        resp = self.app.get('/recommendations',
                            query_string='productId={}'.format(productId))
        self.assertEqual(resp.status_code, HTTP_200_OK)
        self.assertGreater(len(resp.data), 0)
        self.assertIn(productId, resp.data)
        data = json.loads(resp.data)
        return data

    def get_recommendation_count(self):
        """ save the current number of recommendations """
        resp = self.app.get('/recommendations')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = json.loads(resp.data)
        return len(data)

 ######################################################################
 #   M A I N
 ######################################################################
if __name__ == '__main__':
    unittest.main()
