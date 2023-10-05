# Import your dependencies
import os
import datetime
from nylas import APIClient
from dotenv import load_dotenv
import json
import copy

# Load your env variables
load_dotenv()

def initialize_nylas():
    # Initialize your Nylas API client
    nylas = APIClient(
        os.environ.get("CLIENT_ID"),
        os.environ.get("CLIENT_SECRET"),
        os.environ.get("ACCESS_TOKEN"),
    )
    
    return nylas
  
# Get a list of tuples that represent the user's work schedule for the week.
def working_hours(start_time, end_time):
    today = datetime.date.today()

    time_list = []
    
    for day in range(0, 5):
        # https://stackoverflow.com/a/1622052
        weekday = today + datetime.timedelta(days=-today.weekday()) + datetime.timedelta(days=+day)

        weekday_and_start_time = datetime.datetime.combine(weekday, start_time.time())
        weekday_and_start_time_unix = weekday_and_start_time.strftime("%s")

        weekday_and_end_time = datetime.datetime.combine(weekday, end_time.time())
        weekday_and_end_time_unix = weekday_and_end_time.strftime("%s")

        time_list.append((weekday_and_start_time_unix,weekday_and_end_time_unix))
    return time_list

  
# Get the calendar_id for the user's primary calendar
def get_calendar_id(nylas, email):
    calendar_id = ""
    for calendar in nylas.calendars.all():
        # Get the primary calendar for a Google Calendar account
        if calendar["name"] == email:
            calendar_id = calendar["id"]
            break
    if calendar_id == "":
        print("Could not find a calendar for the email #{}, please provide a valid email".format(email))
        sys.exit()
    return calendar_id
  
 
# Make an API call to get all busy periods for each weekday during working hours
def get_all_free_busy(nylas, email, time_list):
    free_busy_week = []
    for time_pair in time_list:
        free_busy = nylas.free_busy(email, time_pair[0], time_pair[1])
        free_busy_week.append(free_busy)
    return free_busy_week
  
# Returns a date in yyyy-mm-dd format for a specified time pair
def get_date_from_time_pair(time_pair):
    return datetime.datetime.fromtimestamp(int(time_pair[0])).strftime('%Y-%m-%d')

def get_date(_time):
	return datetime.datetime.fromtimestamp(int(_time)).strftime('%Y-%m-%d - %H:%M:%S')

# Process free_busy objects to determine when there are blocks of 90+ min of free time
def get_uninterrupted(time_pair, free_busy):
    uninterrupted_time = []
    start_time = time_pair[0]
    end_time = time_pair[1]

    # If the user doesn't have any meetings for the day,
    # return the entire time slot as an uninterrupted time
    if not free_busy[0]["time_slots"]:
        uninterrupted_time.append({
            'start_time': int(start_time),
            'end_time': int(end_time),
        })
        return uninterrupted_time
    
    # Start the search from the beginning of the work day
    previous_start_of_free_time = int(start_time)
    # Iterate through each time_slot and calculate free time
    for time_slot in free_busy[0]["time_slots"]:
        free_time = time_slot["start_time"] - previous_start_of_free_time
        if free_time > 90 * 60:
            uninterrupted_time.append({
                'start_time': previous_start_of_free_time,
                'end_time': time_slot["start_time"],
                })
        previous_start_of_free_time = int(time_slot["end_time"])

    # Check the time between the last meeting and the end of the work day
    last_event_end_time = free_busy[0]["time_slots"][-1]["end_time"]
    free_time_before_eod = int(end_time) - last_event_end_time
    if free_time_before_eod > 90 * 60:
        uninterrupted_time.append({
            'start_time': last_event_end_time,
            'end_time': int(end_time),
            })
    return uninterrupted_time
  
# Process free_busy objects to determine when there are blocks of less than 90 min of free time
def get_fragmented(time_pair, free_busy):
    fragmented_time = []
    start_time = time_pair[0]
    end_time = time_pair[1]

    # If the user doesn't have any meetings for the day,
    # return an empty list
    if not free_busy[0]["time_slots"]:
        return fragmented_time

    # Start the search from the beginning of the work day
    previous_start_of_free_time = int(start_time)
    # Iterate through each time_slot and calculate free time    
    for time_slot in free_busy[0]["time_slots"]:
        free_time = time_slot["start_time"] - previous_start_of_free_time
        if free_time == 0:
            continue
        if free_time < 90 * 60:
            fragmented_time.append({
                'start_time': previous_start_of_free_time,
                'end_time': time_slot["start_time"],
                })
        previous_start_of_free_time = int(time_slot["end_time"])

    # Check the time between the last meeting and the end of the work day
    last_event_end_time = free_busy[0]["time_slots"][-1]["end_time"]
    free_time_before_eod = int(end_time) - last_event_end_time
    if free_time_before_eod < 90 * 60 and free_time_before_eod != 0:
        fragmented_time.append({
            'start_time': last_event_end_time,
            'end_time': int(end_time), })

    return fragmented_time
  

# Identify events that are immediatele before or after a fragmented time slot
def get_unoptimized(calendar_id, time_pair, fragmented_time):
    start_time = int(time_pair[0])
    end_time = int(time_pair[1])
    unoptimized_events = []

    for time_slot in fragmented_time:
        if time_slot["start_time"] != start_time:
            #use a 5 minute buffer to find the event
            end_after = time_slot["start_time"] - 5 * 60
            end_before = time_slot["start_time"] + 5 * 60
            # Query the Nylas Events Endpoint for events within the specified time
            event = nylas.events.where(
                    calendar_id=calendar_id,
                    ends_after=end_after,
                    ends_before=end_before).first()
            if event and event["id"] not in unoptimized_events:
                unoptimized_events.append(event["id"])

        if time_slot["end_time"] != end_time:
            # Use a 5 minute buffer to find events
            start_after = time_slot["end_time"] - 5 * 60
            start_before = time_slot["end_time"] + 5 * 60
            event = nylas.events.where(
                    calendar_id=calendar_id,
                    starts_after=start_after,
                    starts_before=start_before).first()
            if event and event["id"] not in unoptimized_events:
                unoptimized_events.append(event["id"])
    return unoptimized_events


# Take a list of time and calculate the total duration of all the time pairs
def calculate_total_time(time_list):
    total = 0
    for time_pair in time_list:
        total += (time_pair["end_time"] - time_pair["start_time"])
    return int(total / 60)
  

if __name__ == "__main__":
    nylas = initialize_nylas()
    email = nylas.account.email_address
    calendar_id = get_calendar_id(nylas, email)

    # Define start / end times for workday
    start_time = datetime.datetime.strptime("9:30AM", '%I:%M%p')
    end_time = datetime.datetime.strptime("6:00PM", '%I:%M%p')

    # Get time stamps for all work days in the week
    time_list = working_hours(start_time, end_time)
    # Get a user's free-busy info for the work week
    free_busy_week = get_all_free_busy(nylas, email, time_list)

    response = []
    
    # For each day...
    for i in range(0, 5):
        date_object = {}
        # Get a human-readable date format
        date_object["date"] = get_date_from_time_pair(time_list[i])

        # Find the user's uninterrupted focus time and fragmented time
        uninterrupted_time = get_uninterrupted(time_list[i], free_busy_week[i])
        fragmented_time = get_fragmented(time_list[i], free_busy_week[i])
                   
        # Get the unoptimized meetings for the user's week.
        unoptimized_meetings = get_unoptimized(calendar_id, time_list[i], fragmented_time)
        
        # Get date to human readable
        _uninterrupted_time = copy.deepcopy(uninterrupted_time)
        for uninterrupted in _uninterrupted_time:
            uninterrupted['start_time'] = get_date(uninterrupted['start_time'])
            uninterrupted['end_time'] = get_date(uninterrupted['end_time'])

       # Get date to human readable
        _fragmented_time = copy.deepcopy(fragmented_time)
        for fragmented in _fragmented_time:
            fragmented['start_time'] = get_date(fragmented['start_time'])
            fragmented['end_time'] = get_date(fragmented['end_time'])

        # Construct the final JSON response.
        date_object["uninterrupted"] = {
            "minutes": calculate_total_time(uninterrupted_time),
            "time_slots": _uninterrupted_time,
        }
        date_object["fragmented"] = {
            "minutes": calculate_total_time(fragmented_time),
            "time_slots": _fragmented_time,
        }
        date_object["unoptimized_meetings"] = unoptimized_meetings
        response.append(date_object)

    print(json.dumps(response, indent=1))
