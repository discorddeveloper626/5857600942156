import os
import discord
from discord.ext import commands
from flask import Flask, request, redirect, render_template_string
from supabase import create_client
from urllib.parse import urlencode
from datetime import datetime

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="/", intents=intents)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
BOTTOKEN = os.getenv("BOTTOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
ROLE_ID = int(os.getenv("ROLE_ID"))

app = Flask("app")

def save_user(user_info, ip):
    data = {
        "id": user_info["id"],
        "username": f"{user_info['username']}#{user_info['discriminator']}",
        "email": user_info.get("email"),
        "ip": ip,
        "time": str(datetime.utcnow())
    }
    supabase.table("users").upsert(data, on_conflict="id").execute()

@bot.command()
async def button(ctx):
    embed = discord.Embed(
        title="認証システム",
        description="以下のボタンをクリックして Discord 認証を行ってください",
        color=0x5865F2
    )
    url_params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "identify email guilds.join"
    }
    oauth_url = f"https://discord.com/api/oauth2/authorize?{urlencode(url_params)}"

    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="認証する", url=oauth_url))
    await ctx.send(embed=embed, view=view)

@bot.command()
async def data(ctx, user_id: str):
    res = supabase.table("users").select("*").eq("id", user_id).execute()
    if res.data:
        u = res.data[0]
        embed = discord.Embed(title="ユーザー情報", color=0x00FF00)
        embed.add_field(name="ID", value=u["id"])
        embed.add_field(name="Username", value=u["username"])
        embed.add_field(name="Email", value=u.get("email", "N/A"))
        embed.add_field(name="IP", value=u.get("ip", "N/A"))
        embed.add_field(name="登録日時", value=u.get("time", "N/A"))
        await ctx.send(embed=embed)
    else:
        await ctx.send("ユーザーが見つかりません。")

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return render_template_string("<h1 style='color:red;text-align:center'>認証失敗</h1>")

    import requests
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
    token = r.json().get("access_token")

    if not token:
        return render_template_string("<h1 style='color:red;text-align:center'>認証失敗</h1>")

    user_res = requests.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {token}"})
    user_info = user_res.json()

    ip = request.remote_addr
    save_user(user_info, ip)

    guild = bot.get_guild(GUILD_ID)
    if guild:
        member = guild.get_member(int(user_info["id"]))
        if not member:
            async def add_member():
                await guild.fetch_member(int(user_info["id"]))
            bot.loop.create_task(add_member())
        else:
            role = guild.get_role(ROLE_ID)
            if role:
                bot.loop.create_task(member.add_roles(role))
    
    return render_template_string("<h1 style='color:green;text-align:center'>認証成功！</h1>")

if __name__ == "__main__":
    import threading
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000)).start()
    bot.run(BOTTOKEN)
