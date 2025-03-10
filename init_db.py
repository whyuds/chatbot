from sqlalchemy import create_engine, inspect, MetaData, Table, Column, Integer, String, DateTime, func, ForeignKey
from sqlalchemy.types import Text

engine = create_engine('sqlite:///chat.db')
metadata = MetaData()

metadata.reflect(bind=engine)

def initialize_db():
    with engine.connect() as connection:
        if not inspect(connection).has_table('conversations'):
            conversations = Table(
                'conversations', metadata,
                Column('id', Integer, primary_key=True, autoincrement=True),
                Column('title', String(255)),
                Column('created_at', DateTime, server_default=func.now()),
                Column('updated_at', DateTime, server_default=func.now(), onupdate=func.now())
            )
            messages = Table(
                'messages', metadata,
                Column('id', Integer, primary_key=True, autoincrement=True),
                Column('conversation_id', Integer, ForeignKey('conversations.id')),
                Column('role', String(50)),
                Column('content', Text),
                Column('created_at', DateTime, server_default=func.now())
            )
            metadata.create_all(engine)

if __name__ == '__main__':
    initialize_db()
    print("Database initialized successfully")
