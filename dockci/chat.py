""" Module for chat integration, for DockCI """
import hypchat

#pylint:disable=too-few-public-methods
class Chat():
    """ Chat Class generic """

    def __init__(self, apitoken, room):
        self.token = apitoken
        self.roomname = room
        self.roomid = 0
        # probaly need this in a try catch
        self.chatconn = hypchat.HypChat(apitoken)

    def _verify_room(self):
        """ check to see if room exists on hipchat and get roomid """
        rooms = self.chatconn.rooms()
        roomlist = rooms['items']
        for room in roomlist:
            if room['name'] == self.roomname:
                self.roomid = room['id']
                return True
        return False

    def message(self, mymessage):
        """ Prints message to Room """
        if self._verify_room():
            room = self.chatconn.get_room(self.roomid)
            room.message(mymessage)
