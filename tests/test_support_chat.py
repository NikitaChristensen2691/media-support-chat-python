from support_chat import ChatRequest, ChatResult, CreatorDelivery, handle_chat


class FakeClient:
    def __init__(self):
        self.calls = []

    def create_channel(self, channel):
        self.calls.append(("create", channel))

    def publish(self, channel, event, data, account_id):
        self.calls.append(("publish", channel, event, data, account_id))

    def presence(self, channel):
        self.calls.append(("presence", channel))
        return {"online": 1}

    def send_email(self, to, subject, body):
        self.calls.append(("email", to, subject, body))
        return "msg-123"


def test_leaving_visitor_gets_one_channel_and_transcript_email():
    client = FakeClient()
    request = ChatRequest(
        "v7",
        "Caption issue",
        "Captions are late.",
        "Visitor: Captions are late.",
        CreatorDelivery("asset-9", "job-4", "creator-2"),
    )
    result = handle_chat(request, "support@example.com", client)

    assert result == ChatResult("media-support-v7", "msg-123")
    assert [call[0] for call in client.calls] == ["create", "publish", "presence", "email"]
    assert client.calls[-1][3] == "Visitor: Captions are late."
