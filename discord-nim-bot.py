import time
import random
import asyncio
import discord
from nim import train, Nim
from pymongo import MongoClient
from discord.ext import commands

with open('credentials.txt', 'r') as file:
    texts = file.readlines()
    texts = [line.rstrip() for line in texts]

cluster = MongoClient(texts[1])
db = cluster["MyDatabase"]
collection = db["MyCollection"]

ai = train(10000)

client = commands.Bot(command_prefix='!')

@client.event
async def on_ready():
    print('Identity:', client.user)
    game = discord.Game('Nim')
    await client.change_presence(status=discord.Status.online, activity=game)

@client.event
async def on_member_join(member):
    await member.create_dm()
    await member.dm_channel.send(f'Welcome {member.name} to my server, you can play Nim with AI in general channel')

@client.event
async def on_message(message):
    # prevent self loop
    if message.author == client.user:
        return
    if message.content == 'ping':
        await message.channel.send('pong')
    if message.content.lower() == 'hi':
        await message.channel.send(f"Nice to meet you! {message.author.mention}")
    
    await client.process_commands(message)

# --------------------------------- NIM --------------------------------- #

@client.command()
async def play(ctx):
    await ctx.channel.send('Game Started!')

    def check(message):
        return message.author == ctx.author and message.channel == ctx.channel

    human_player = random.randint(0, 1)

    # Create new game
    game = Nim()

    # Game loop
    while True:

        # Print contents of piles
        piles= []
        piles.append("```Piles:")
        for i, pile in enumerate(game.piles):
            piles.append(f"Pile {i}: {pile}")
        await ctx.send('\n'.join(piles) + '```')

        # Compute available actions
        available_actions = Nim.available_actions(game.piles)
        time.sleep(1)

        # Let human make a move
        if game.player == human_player:
            await ctx.channel.send("Your Turn")
            while True:
                try:
                    await ctx.channel.send("```Choose Pile: ```")
                    pile = await client.wait_for('message', check=check, timeout=20)
                    await ctx.channel.send("```Choose Count: ```")
                    count = await client.wait_for('message', check=check, timeout=20)
                except asyncio.TimeoutError:
                    await ctx.channel.send("```Timeout, please enter your move again.```")
                    continue

                try:
                    pile = int(pile.content)
                    count = int(count.content)
                except ValueError:
                    await ctx.channel.send("```Invalid input, try again.```")
                    continue

                if (pile, count) in available_actions:
                    break
                await ctx.channel.send("```Invalid move, try again.```")

        # Have AI make a move
        else:
            await ctx.channel.send("AI's Turn")
            pile, count = ai.choose_action(game.piles, epsilon=False)
            await ctx.channel.send(f"```AI chose to take {count} from pile {pile}.```")

        # Make move
        game.move((pile, count))

        # Check for winner
        if game.winner is not None:
            winner = "Human" if game.winner == human_player else "AI"
            await ctx.channel.send(f"```GAME OVER. Winner is {winner}```")
            update_score(game.winner == human_player, ctx.author.id)
            return

def update_score(result, id):
    query = { "_id": id }
    if (collection.count_documents(query) == 0):
        post = {"_id": id, "score": 0, "AI_score": 0}
        post["score"] = 1 if result == 1 else 0
        post["AI_score"] = 1 if result == 0 else 0
        collection.insert_one(post)
    else:
        user = collection.find(query)
        for doc in user:
            score = doc["score"]
            AI_score = doc["AI_score"]

        if result == 1:
            score += 1
        else:
            AI_score += 1

        collection.update_one({"_id":id}, {"$set":{"score":score, "AI_score":AI_score}})

@client.command()
async def history(ctx):
        query = { "_id": ctx.author.id }
        score = 0
        AI_score = 0

        if (collection.count_documents(query) == 0):
            post = {"_id": ctx.author.id, "score": 0, "AI_score": 0}
            collection.insert_one(post)
        else:
            user = collection.find(query)
            for result in user:
                score = result["score"]
                AI_score = result["AI_score"]
        
        message = "```" + str(ctx.author) + "'s match history against AI:\nWins: " + str(score) + "\nLosses: " + str(AI_score) + "```"
        await ctx.channel.send(message)

client.run(texts[0])
