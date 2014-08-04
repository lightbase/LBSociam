#!/usr/env python
# -*- coding: utf-8 -*-
import lbsociam
import unittest
from liblightbase import lbrest
from lbsociam.model import lbtwitter
from liblightbase.lbutils import conv
from liblightbase.lbbase.struct import Base

from . import test_twitter_import

class TwitterBaseTestCase(test_twitter_import.TwitterImportTestCase):
    """
    Test LB integration
    """

    def setUp(self):
        """
        Load test data
        """
        test_twitter_import.TwitterImportTestCase.setUp(self)

        self.lbs = lbsociam.LBSociam()
        self.baserest = lbrest.BaseREST(rest_url=self.lbs.lbgenerator_rest_url, response_object=True)
        self.lbt = lbtwitter.Twitter(debug=True, term='crime')
        pass

    def test_communication(self):
        """
        Test communication to LB database
        """
        response = self.baserest.search()
        assert response.status_code == 200

    def test_generate_base(self):
        """
        Auto generate LBBase from status object
        """
        status = self.lbt.search()
        # Remove repeated elements
        status_elm = status[0]
        del status_elm._user._created_at
        del status_elm._user._location

        lbbase = conv.pyobject2base(status_elm)
        fd = open('/tmp/status_base.json', 'w+')
        fd.write(lbbase.json)
        fd.close()
        self.assertIsInstance(lbbase, Base)

    def test_base_to_json(self):
        """
        Test auto generated base json conversion back to base
        """
        status = self.lbt.search()
        # Remove repeated elements
        status_elm = status[0]
        del status_elm._user._created_at
        del status_elm._user._location

        lbbase = conv.pyobject2base(status_elm)
        j = lbbase.json
        b = conv.json2base(j)
        self.assertIsInstance(b, Base)

    def test_create_remove_base(self):
        """
        Test Base object creation from Twitter class method
        """
        status = self.lbt.search()
        lbbase = self.lbt.create_base(status[0])
        self.assertIsInstance(lbbase, Base)
        result = self.lbt.remove_base(lbbase)
        assert(result)


    def test_status_to_document(self):
        """
        Test Status conversion to LB Document
        """
        status = self.lbt.search()
        lbbase = self.lbt.create_base(status[0])
        TwitterStatus = lbbase.metaclass()
        status_dict = self.lbt.status_to_dict(status)
        print(status_dict[0]['_user'].keys())
        status_obj = conv.json2document(lbbase, status_dict[0])
        self.assertIsInstance(status_obj, TwitterStatus)
        result = self.lbt.remove_base(lbbase)
        assert(result)

    def tearDown(self):
        """
        Clear test data
        """
        test_twitter_import.TwitterImportTestCase.tearDown(self)
        pass
