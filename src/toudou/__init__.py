import os

config = dict(
    DATABASE_URL=os.getenv('TOUDOU_DATABASE_URL', ''),
    DEBUG=True
)
# print(config)

