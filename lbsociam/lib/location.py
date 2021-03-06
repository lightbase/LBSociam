#!/usr/env python
# -*- coding: utf-8 -*-
__author__ = 'eduardo'

import logging
import json
import re
import time
from lbsociam.model import gmaps
from googlemaps.exceptions import ApiError, TransportError, Timeout, _RetriableRequest
from lbsociam.model import location as loc

log = logging.getLogger()

# Wakeup time if Search APi is sleeping
wakeup_time = None


def get_location(status, cache=True):
    """
    Get location for status
    :param status: status dict
    :param cache: Use cache to store and retrieve results
    :return: status with location
    """
    log.debug("LOCATION: processing id_doc = %s", status['_metadata']['id_doc'])
    source = json.loads(status['source'])
    source = source[0]
    status['location'] = dict()
    location_base = loc.LocationBase()

    geo = source.get('_geo')
    if geo is not None:
        latitude = geo['coordinates'][0]
        longitude = geo['coordinates'][1]

        status['location']['latitude'] = latitude
        status['location']['longitude'] = longitude

        # Register source
        status['location']['loc_origin'] = 'geo'

        return status

    coordinates = source.get('_coordinates')
    if coordinates is not None:
        # Try Coordinates
        status['location']['latitude'] = coordinates[0]
        status['location']['longitude'] = coordinates[1]

        # Register source
        status['location']['loc_origin'] = 'coordinates'

        return status

    location = source.get('_location')
    if location is not None:
        # Check for empty string
        if location:
            # Try to use cache first
            if cache:
                result = location_base.get_location(location)
                if result is None:
                    result = maps_search(location)
                    if result is not None:
                        # This is the string used on search
                        result['city'] = location
                        id_doc = location_base.add_location(result)
                        log.debug("New location stored. id_doc = %s", id_doc)
                        status['location']['id_location'] = id_doc

            else:
                result = maps_search(location)

            if result is not None:
                status['location']['latitude'] = result['latitude']
                status['location']['longitude'] = result['longitude']
                status['location']['city'] = result['location_name']

                # Register source
                status['location']['loc_origin'] = 'location'

                return status

    # Focus: use SRL to find location
    for structure in status['arg_structures']:
        for argument in structure['argument']:
            argument_name = argument['argument_name']
            log.debug("LOCATION: search in argument_name = %s", argument_name)

            if re.match('.*-LOC', argument_name) is not None:
                # Convert list os values to string
                location = " ".join(argument['argument_value'])
                log.info("LOCATION: string match for argument_name = %s. Location = %s", argument_name, location)
                # Try to use cache first
                if cache:
                    result = location_base.get_location(location)
                    if result is None:
                        result = maps_search(location)
                        if result is not None:
                            # This is the string used on search
                            result['city'] = location
                            id_doc = location_base.add_location(result)
                            log.debug("New location stored. id_doc = %s", id_doc)
                            status['location']['id_location'] = id_doc
                else:
                    result = maps_search(argument['argument_value'])

                if result is not None:
                    status['location']['latitude'] = result['latitude']
                    status['location']['longitude'] = result['longitude']
                    status['location']['city'] = result['location_name']

                    # Register source
                    status['location']['loc_origin'] = 'srl'

                    return status

    # Last try: consider user location
    user = source.get('_user')
    if user is not None:
        geo = user.get('_geo')
        if geo is not None:
            latitude = geo['coordinates'][0]
            longitude = geo['coordinates'][1]

            status['location']['latitude'] = latitude
            status['location']['longitude'] = longitude

            # Register source
            status['location']['loc_origin'] = 'user_geo'

            return status

        coordinates = user.get('_coordinates')
        if coordinates is not None:
            # Try Coordinates
            status['location']['latitude'] = coordinates[0]
            status['location']['longitude'] = coordinates[1]

            # Register source
            status['location']['loc_origin'] = 'user_coordinates'

            return status

        location = user.get('_location')
        if location is not None:
            # Check for empty string
            if location:
                # Try to use cache first
                if cache:
                    result = location_base.get_location(location)
                    if result is None:
                        result = maps_search(location)
                        if result is not None:
                            # This is the string used on search
                            result['city'] = location
                            id_doc = location_base.add_location(result)
                            log.debug("New location stored. id_doc = %s", id_doc)
                            status['location']['id_location'] = id_doc
                else:
                    result = maps_search(location)

                if result is not None:
                    status['location']['latitude'] = result['latitude']
                    status['location']['longitude'] = result['longitude']
                    status['location']['city'] = result['location_name']

                    # Register source
                    status['location']['loc_origin'] = 'user_location'

                    return status

    # If I'm here, it was not possible to find the location
    log.error("LOCATION: Location not found for status id = %s", status['_metadata']['id_doc'])
    del status['location']

    return status


def maps_search(location):
    """
    Search for location in Google Maps API
    :param location: text location identified
    :return: dict with latitude and longitude
    """
    log.debug("SEARCH: location %s", location)

    if wakeup_time is not None:
        # Check if it is time to wakeup
        now = time.time()
        if now > wakeup_time:
            log.info("LOCATION: Waking up at %s", time.ctime())
            # Set sleep time to None
            set_wakeup_time(None)
        else:
            log.debug("Wakeup time %s not reached at %s", time.ctime(wakeup_time), time.ctime())
            return None

    maps = gmaps.GMaps()
    try:
        result = maps.client.geocode(location)

        if len(result) == 0:
            return None

    except _RetriableRequest as e:
        log.error("LOCATION: Limite de API excedido. Esperando 24h...")
        log.error(e.message)
        log.info("LOCATION: Sleeping at %s", time.ctime())
        # This will make it sleep 24 hours
        w_time = time.time() + 86400
        set_wakeup_time(w_time)
        return None

    except ApiError as e:
        log.error("LOCATION: Location not found\n%s", e)
        return None

    except TransportError as e:
        log.error("LOCATION: Location not found\n%s", e)
        return None

    except Timeout as e:
        log.error("LOCATION: Location not found\n%s", e)
        return None

    # As a start, select first random result
    try:
        lat = result[0]['geometry']['location']['lat']
        lng = result[0]['geometry']['location']['lng']
        loc = result[0]['address_components'][0]['long_name']
        type = result[0]['geometry']['location_type']
    except IndexError as e:
        log.error("Invalid results %s\n%s", result, e)
        lat = result['geometry']['location']['lat']
        lng = result['geometry']['location']['lng']
        loc = result['address_components'][0]['long_name']
        type = result['geometry']['location_type']

    result_dict = {
        'latitude': lat,
        'longitude': lng,
        'location_name': loc,
        'location_type': type,
        'loc_origin': 'GMaps'
    }

    log.debug("SEARCH: result dict: %s", result_dict)

    return result_dict


def set_wakeup_time(w_time):
    global wakeup_time
    wakeup_time = w_time