"""
Client model for krema.
"""

from unikorn import kollektor
from ..errors import FetchChannelFailed, InvalidTokenError


class Client:
    """Base class for client.

    Args:
        intents (int): Intents for your bot. Do not add any intent if you are using for self-bot.
        cache_limit (int): Cache limit for krema. 

    Attributes:
        token (str): Bot token for http request.
        events (list): List of events for client.
        user (User): Client user.
        messages (kollektor.Kollektor): Message cache.
        connection (Gateway): Client gateway.
        connection (HTTP): Client http class.
    """

    def __init__(self, intents: int = 0, cache_limit: int = 200) -> None:
        from .user import User

        self.intents: int = intents
        self.cache_limit: int = cache_limit

        self.token: str = ""
        self.events: list = []
        self.user: User = None

        self.messages: kollektor.Kollektor = kollektor.Kollektor()

        self.connection = None
        self.http = None

        self.__add_cache_events()
        pass

    @property
    def formatted_token(self) -> str:
        """Returns formatted version of the token.

        Returns:
            str: Formatted version of the token.
        """

        if self.token.startswith("Bot "):
            return self.token.split(" ")[1]
        else:
            return self.token

    def event(self, event_name: str = None):
        """Event decorator for handle gateway events.

        Args:
            event_name (str, optional): Event name in lowercase. Example MESSAGE_CREATE is message_create for krema. If you don't add this argument, It will get the name from function name.

        """

        def decorator(fn):
            def wrapper():
                self.events.append(
                    (event_name or fn.__name__, fn)
                )

                return self.events

            return wrapper()

        return decorator

    async def check_token(self):
        """Check token status for client.

        Returns:
            None: Client token works.

        Raises:
            InvalidTokenError: Checking the token is failed, probably your token is broken.
        """

        from .user import User
        atom, result = await self.http.request("GET", "/users/@me")

        if atom == 1:
            raise InvalidTokenError(
                "Token is invalid. Please check your token!")
        else:
            self.user = User(self, result)

    def start(self, token: str, bot: bool = True):
        """Start the client.

        Args:
            token (str): Token for your bot / self-bot.
            bot (bool, optional): If you are using self-bot, make argument false.
        """

        from ..gateway import Gateway
        from ..http import HTTP

        self.token = f"Bot {token}" if bot else token

        self.connection = Gateway(self)
        self.http = HTTP(self)

        self.connection._event_loop.run_until_complete(self.check_token())
        self.connection._event_loop.run_until_complete(
            self.connection.start_connection())

    # Handler for Cache Events.
    def __add_cache_events(self):
        # Message Add Handler
        async def _message_create(message_packet):
            self.messages.append(message_packet)

        # Message Update Handler
        async def _message_update(message_packet):
            for index, message in enumerate(self.messages.items):
                if message.id == message_packet.id:
                    self.messages.update(index, message_packet)
                    break

        # Message Delete Handler
        async def _message_delete(packet):
            message_id = packet.get("id")

            if message_id is None:
                return
            else:
                message_id = int(message_id)

                for message in self.messages.items:
                    if message.id == message_id:
                        self.messages.items = tuple(
                            i for i in self.messages.items if i.id != message.id)
                        break

        # Message Bulk Delete Handler
        async def _message_bulk_delete(packet):
            message_ids = packet.get("ids")

            if message_ids is None:
                return
            else:
                message_ids = tuple(int(i) for i in message_ids)
                self.messages.items = tuple(
                    i for i in self.messages.items if i.id not in message_ids)

        event_list: dict = {
            "message_create": _message_create,
            "message_update": _message_update,
            "message_delete": _message_delete,
            "message_delete_bulk": _message_bulk_delete,
        }

        # Load Events
        self.events.extend(
            (key, value) for key, value in event_list.items()
        )

    # Gateway Function
    # ==================

    async def update_presence(self, packet: dict):
        """Update client-user presence.

        Args:
            packet (dict): https://discord.com/developers/docs/topics/gateway#update-presence-gateway-presence-update-structure
        """

        await self.connection.websocket.send_json({
            "op": 3,
            "d": packet
        })

    # Endpoint Functions
    # ==================

    async def fetch_channel(self, id: int):
        """Fetch a channel by ID.

        Args:
            id (int): Channel ID.

        Returns:
            Channel: Found channel.

        Raises:
            FetchChannelFailed: Fetching the channel is failed.
        """

        from .guild import Channel

        atom, result = await self.http.request("GET", f"/channels/{id}")

        if atom == 0:
            return Channel(self,  result)
        else:
            raise FetchChannelFailed(result)
