from pyecore.resources import URI
from io import BytesIO

class BytesURI(URI):
    def __init__(self, uri, bytes=None):
        super(BytesURI, self).__init__(uri)
        if bytes is not None:
            self.__stream = BytesIO(bytes)

    def getvalue(self):
        return self.__stream.getvalue()

    def create_instream(self):
        return self.__stream

    def create_outstream(self):
        self.__stream = BytesIO()
        return self.__stream
