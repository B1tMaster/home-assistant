"""
Facebook platform for notify component.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/notify.facebook/
"""
import json
import logging

from aiohttp.hdrs import CONTENT_TYPE
import requests
import voluptuous as vol

from homeassistant.components.notify import (
    ATTR_DATA, ATTR_TARGET, PLATFORM_SCHEMA, BaseNotificationService)
from homeassistant.const import CONTENT_TYPE_JSON
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

CONF_PAGE_ACCESS_TOKEN = 'page_access_token'
BASE_URL = 'https://graph.facebook.com/v2.6/me/messages'
CREATE_BROADCAST_MSG_URL = 'https://graph.facebook.com/v2.11/me/message_creatives'
BROADCAST_MSG_URL = 'https://graph.facebook.com/v2.11/me/broadcast_messages'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_PAGE_ACCESS_TOKEN): cv.string,
})


def get_service(hass, config, discovery_info=None):
    """Get the Facebook notification service."""
    return FacebookNotificationService(config[CONF_PAGE_ACCESS_TOKEN])


class FacebookNotificationService(BaseNotificationService):
    """Implementation of a notification service for the Facebook service."""

    def __init__(self, access_token):
        """Initialize the service."""
        self.page_access_token = access_token

    def send_message(self, message="", **kwargs):
        """Send some message."""
        payload = {'access_token': self.page_access_token}
        targets = kwargs.get(ATTR_TARGET)
        data = kwargs.get(ATTR_DATA)

        body_message = {"text": message}

        if data is not None:
            body_message.update(data)
            # Only one of text or attachment can be specified
            if 'attachment' in body_message:
                body_message.pop('text')

        if not targets:
            _LOGGER.error("At least 1 target is required")
            return

        # broadcast message
        if targets[0].startswith('BROADCAST'):

            brdcast_create_body = {"messages": [body_message]}

            _LOGGER.debug("FB Messager broadcast body full  %s : ", brdcast_create_body)

            resp = requests.post(CREATE_BROADCAST_MSG_URL, data=json.dumps(brdcast_create_body),
                                 params=payload,
                                 headers={CONTENT_TYPE: CONTENT_TYPE_JSON},
                                 timeout=10)
            _LOGGER.info("FB Messager broadcast id %s : ", resp.json())

            # at this point we get broadcast id
            brdcast_body = {
                "message_creative_id": resp.json().get('message_creative_id'),
                "notification_type": "REGULAR",
            }

            resp = requests.post(BROADCAST_MSG_URL, data=json.dumps(brdcast_body),
                                 params=payload,
                                 headers={CONTENT_TYPE: CONTENT_TYPE_JSON},
                                 timeout=10)
            if resp.status_code != 200:
                obj = resp.json()
                error_message = obj['error']['message']
                error_code = obj['error']['code']
                _LOGGER.error(
                    "Error %s : %s (Code %s)", resp.status_code, error_message,
                    error_code)

        # non-broadcast message
        else:

            for target in targets:
                # If the target starts with a "+", we suppose it's a phone number,
                # otherwise it's a user id.
                if target.startswith('+'):
                    recipient = {"phone_number": target}
                else:
                    recipient = {"id": target}

                body = {
                    "recipient": recipient,
                    "message": body_message
                }
                resp = requests.post(BASE_URL, data=json.dumps(body),
                                     params=payload,
                                     headers={CONTENT_TYPE: CONTENT_TYPE_JSON},
                                     timeout=10)
                if resp.status_code != 200:
                    obj = resp.json()
                    error_message = obj['error']['message']
                    error_code = obj['error']['code']
                    _LOGGER.error(
                        "Error %s : %s (Code %s)", resp.status_code, error_message,
                        error_code)


