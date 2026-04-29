import asyncio
from dbus_next.aio import MessageBus
from dbus_next import Variant

async def main():
    bus = await MessageBus().connect()
    
    # 1. Quét tìm Brave
    introspection = await bus.introspect('org.freedesktop.DBus', '/org/freedesktop/DBus')
    obj = bus.get_proxy_object('org.freedesktop.DBus', '/org/freedesktop/DBus', introspection)
    dbus = obj.get_interface('org.freedesktop.DBus')
    names = await dbus.call_list_names()
    
    players = [n for n in names if n.startswith('org.mpris.MediaPlayer2.brave')]
    print(f"Brave Players Found: {players}")

    for service in players:
        try:
            # 2. Lấy Metadata TRỰC TIẾP không cần introspect (để tránh treo)
            # Chúng ta gọi Interface org.freedesktop.DBus.Properties
            # Method Get(interface_name, property_name)
            
            # Vì không introspect, ta dùng bus.call trực tiếp
            from dbus_next import Message, MessageType
            
            reply = await bus.call(Message(
                destination=service,
                path='/org/mpris/MediaPlayer2',
                interface='org.freedesktop.DBus.Properties',
                member='Get',
                signature='ss',
                body=['org.mpris.MediaPlayer2.Player', 'Metadata']
            ))
            
            if reply.message_type == MessageType.METHOD_RETURN:
                # Metadata là một Variant chứa Dict
                metadata = reply.body[0].value
                print(f"\n--- Metadata for {service} ---")
                for k, v in metadata.items():
                    val = v.value if hasattr(v, 'value') else v
                    print(f"{k}: {val}")
            else:
                print(f"Failed to get metadata for {service}")
                
        except Exception as e:
            print(f"Error accessing {service}: {e}")

if __name__ == "__main__":
    asyncio.run(main())