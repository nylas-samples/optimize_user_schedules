# optimize_user_schedules

The example below shows how to use the Nylas Calendar API to build a calendar integration that allows users to track how much uninterrupted focus time, as well as fragmented time they have on their schedule. It also identifies unoptimized meetings that can be moved to increase the amount of uninterrupted focus time users have.

## Setup

### System dependencies

- Python v3.x

### Gather environment variables

You'll need the following values:

```text
CLIENT_ID = ""
CLIENT_SECRET = ""
ACCESS_TOKEN = ""
```

Add the above values to a new `.env` file:

```bash
$ touch .env # Then add your env variables
```

Run the file **Optimize_User_Schedules.py**:

```bash
$ python3 Optimize_User_Schedules.py
```

## Learn more

Visit our [Nylas Python SDK documentation](https://developer.nylas.com/docs/developer-tools/sdk/python-sdk/) to learn more.
