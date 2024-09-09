import discord
from discord.ext import commands

import regex as re
import pytz
from datetime import datetime 
from timezonefinder import TimezoneFinder

import random
from geopy.geocoders import Nominatim  
import csv

import os
import requests
from dotenv import load_dotenv
load_dotenv()

#from geminiwork import translatetxt



client = commands.Bot(command_prefix="+",intents=discord.Intents.all())
games = {}

flag_map = {}

#fxn for weather command
def get_weather(city_name):
    api_key = os.getenv("WEATHER_API_KEY")  
    base_url = "http://api.openweathermap.org/data/2.5/weather?"
    
    complete_url = base_url + "q=" + city_name + "&appid=" + api_key + "&units=metric"

    response = requests.get(complete_url)

    if response.status_code == 200:
        data = response.json()

        main = data['main']
        weather = data['weather'][0]
        wind = data['wind']

        # Format the weather data
        weather_report = (
            f"*Weather in {city_name.capitalize()}*\n"
            f"Temperature: {main['temp']}°C\n"
            f"Humidity: {main['humidity']}%\n"
            f"Condition: {weather['description'].capitalize()}\n"
            f"Wind Speed: {wind['speed']} m/s"
        )
        return weather_report
    else:
        print(response.json())
        return "Sorry, I couldn't retrieve weather data for that location."

@client.event
async def on_ready():
    print("Bot is successfully connected to Discord")
 
@client.command()
async def ping(ctx):
    await ctx.send("Pong")  


#1. Guess the number

@client.command(name="gnm")
async def start_game(ctx):
    user = ctx.author
    games[user.id] = {
        "key": random.randint(1, 101),
        "attempts": 5
    }
    await ctx.send(f"{user.mention}, the game has started! You have 5 attempts to guess the number between 1 and 100.")

@client.command(name="guess")
async def guess(ctx, number: int):
    user = ctx.author
    if user.id not in games:
        await ctx.send(f"{user.mention}, you need to start a game first with `+gnm`!")
        return

    game = games[user.id]
    if game["attempts"] <= 0:
        await ctx.send(f"{user.mention}, you have no attempts left! The correct number was {game['key']}. Start a new game with `+gnm`.")
        del games[user.id]
        return

    if number == game["key"]:
        await ctx.send(f"Congratulations {user.mention}! You guessed the number {game['key']} correctly! You won!")
        del games[user.id]
    elif number > game["key"]:
        game["attempts"] -= 1
        await ctx.send(f"{user.mention}, your guess is high! Attempts left: {game['attempts']}")
    else:
        game["attempts"] -= 1
        await ctx.send(f"{user.mention}, your guess is low! Attempts left: {game['attempts']}")

    if game["attempts"] <= 0:
        await ctx.send(f"Sorry {user.mention}, you have no attempts left. You lost! The correct number was {game['key']}. Start a new game with `+gnm`.")
        del games[user.id]





#2. Location Fetcher with Flag
with open('files/DiscordCF.csv', 'r', encoding='utf-8') as file:
    reader = csv.reader(file)
    next(reader)  
    for row in reader:
        flag_code = row[0].strip()  
        country = row[1].strip()  
        flag_map[country] = flag_code

@client.command(name="loc")
async def get_location(ctx, coordinates: str):
    geolocator = Nominatim(user_agent="discord-bot")


    try:
        lat, lon = map(float, coordinates.split(','))

        location = geolocator.reverse((lat, lon), exactly_one=True , language='en')
        #location = geolocator.reverse(location, language='en')

        
        # Extract from location
        if location:
            address = location.raw['address']
            country = address.get('country', 'Unknown country')
            #tc= translatetxt(country)
            city = address.get('city', address.get('town', address.get('village', 'Unknown city')))
            #tct= translatetxt(city)
            state = address.get('state', 'Unknown state')
            #ts = translatetxt(state)
            # response message
            response = f"Country: {country}\nCity: {city}\nState: {state}"

            # Check if the country exists 
            if country in flag_map:
                flag_code = flag_map[country]
                response += f"\nFlag: {flag_code}"

                # Send message
                message = await ctx.send(response)

                # React to the message with the corresponding emoji code (this needs to be the actual emoji)
                # await message.add_reaction('<:flag_cg:🇨🇬>')
            else:
                # Send the response without flag if the country is not found in the map
                await ctx.send(response)
        else:
            await ctx.send(f"{ctx.author.mention}, location details not found for the given coordinates.Probably Ocean or Sea")
    except ValueError:
        await ctx.send(f"{ctx.author.mention}, please provide valid coordinates in the format `latitude,longitude`.")
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")

#3. Weather Command
@client.command(name="weather")
async def weather(ctx, *, city: str):
    weather_report = get_weather(city)
    await ctx.send(weather_report)


# Listen for messages
@client.event

async def on_message(message):
    if message.author == client.user:
        return

    #4. Calculator feature
    if re.search(r'(\d+(\.\d+)?)\s*([+\-*/])\s*(\d+(\.\d+)?)', message.content):
        calculation = re.search(r'(\d+(\.\d+)?)\s*([+\-*/])\s*(\d+(\.\d+)?)', message.content).group()
        try:
            result = eval(calculation)
            rounded_result = round(result, 2)
            await message.channel.send(f'The result of {calculation} is: {rounded_result}')
        except ZeroDivisionError:
            await message.channel.send('Error: Division by zero is not allowed.')
        except Exception as e:
            await message.channel.send(f'Error occurred during calculation: {e}')

    #5.Timezone feature
    if re.search(r'time\s+in\s+([\w\s]+)', message.content, re.IGNORECASE):
        city = re.search(r'time\s+in\s+([\w\s]+)', message.content, re.IGNORECASE).group(1)
        geolocator = Nominatim(user_agent="discord-bot")
        timezone_finder = TimezoneFinder()
        try:
            location = geolocator.geocode(city)
            if location:
                lat, lon = location.latitude, location.longitude
                tz = pytz.timezone(timezone_finder.timezone_at(lng=lon, lat=lat))
                current_time = datetime.now(tz).strftime('%d-%m-%Y %H:%M:%S')
                await message.channel.send(f'The current time in {city} is: {current_time}')
            else:
                await message.channel.send('Error: City not found.')
        except Exception as e:
            await message.channel.send(f'Error occurred during time retrieval: {e}')

    await client.process_commands(message)


client.run(os.getenv("SECRET"))



