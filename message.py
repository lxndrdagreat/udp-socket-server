import json

class MessageProtocol:

    def create(self, msg_type, payload):
        msg = {
            "t": msg_type,
            "p": payload
        }
        msg_json = "{}\n".format(json.dumps(msg))
        return bytes(msg_json, "utf-8")

    def parse(self, message):
        parsed = json.loads(message.decode("utf-8").strip())
        return parsed["t"], parsed["p"]