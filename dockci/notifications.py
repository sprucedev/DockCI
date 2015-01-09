""" Module for notification integration, for DockCI """
import logging
import hypchat

# pylint:disable=too-few-public-methods


class HipChat():
    """ HipChat Class """

    def __init__(self, apitoken, room):
        self.token = apitoken
        self.roomname = room
        self.roomid = None
        self.chatconn = None
        self._create_connection()
        self._fetch_roomid()

    def _create_connection(self):
        """ Initialises a connection to the HipChat server """
        # TODO: this connection should be cached and handle reconnects, etc..
        self.chatconn = None
        try:
            # HypChat() doesn't initiate a connection, invoke rooms() to test
            conn = hypchat.HypChat(self.token)
            conn.rooms()
            self.chatconn = conn
        except hypchat.requests.HttpUnauthorized:
            logging.exception("HipChat Connection failed - Invalid API Token")
        except Exception:  # pylint:disable=broad-except
            logging.exception("Unknown error")

    def _fetch_roomid(self):
        """ Check to see if room exists on hipchat and get roomid """
        if self.chatconn is not None:
            rooms = self.chatconn.rooms()
            roomlist = rooms['items']
            for room in roomlist:
                if room['name'] == self.roomname:
                    self.roomid = room['id']
                    break
        else:
            logging.warning("HipChat Connection has not been established yet")

    def message(self, mymessage):
        """ Prints message to HipChat Room """
        if self.roomid is not None:
            room = self.chatconn.get_room(self.roomid)
            room.message(mymessage)
        else:
            logging.warning("HipChat Room ID has not been set")
