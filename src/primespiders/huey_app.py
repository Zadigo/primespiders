import dotenv
from huey import RedisHuey

dotenv.load_dotenv('.env')

huey_app = RedisHuey(name='primespiders')


@huey_app.task(retries=3)
def test_task():
    print("This is a test task.")


if __name__ == '__main__':
    pass
