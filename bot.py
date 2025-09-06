import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Setup logging
log_dir = Path('/logs')
if not log_dir.exists():
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'bot.log'),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID', 0))
FORUM_CHANNEL_ID = int(os.getenv('FORUM_CHANNEL_ID', 0))

if not TOKEN:
    logging.error("DISCORD_BOT_TOKEN not found!")
    sys.exit(1)

class ForumBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        # Add commands to tree
        self.tree.add_command(self.add_tags_cmd)
        self.tree.add_command(self.add_posts_cmd)
        self.tree.add_command(self.list_tags_cmd)  # This one stays public
        self.tree.add_command(self.delete_posts_cmd)
        
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print("✅ Slash commands synced to guild!")

    # Admin-only commands
    @app_commands.command(name="add-tags", description="Create forum tags")
    @app_commands.default_permissions(administrator=True)
    async def add_tags_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_message('🏷️ Creating forum tags...')
        await self.create_forum_tags(interaction)

    @app_commands.command(name="add-posts", description="Create forum posts")
    @app_commands.default_permissions(administrator=True)
    async def add_posts_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'📝 Creating {len(posts_data)} forum posts...')
        await self.create_forum_posts(interaction)

    # Public command (no permissions decorator)
    @app_commands.command(name="list-tags", description="Show available forum tags")
    async def list_tags_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.list_available_tags(interaction)

    # Admin-only with custom permissions
    @app_commands.command(name="delete-posts", description="Delete all bot-created forum posts")
    @app_commands.default_permissions(manage_messages=True)  # Or any specific permission
    async def delete_posts_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_message('🗑️ Searching for bot-created forum posts...')
        await self.delete_bot_posts(interaction)

    async def create_forum_tags(self, interaction):
        guild = self.get_guild(GUILD_ID)
        forum_channel = guild.get_channel(FORUM_CHANNEL_ID)
        
        existing_tag_names = {tag.name.lower() for tag in forum_channel.available_tags}
        
        new_tags = []
        tags_to_add = []
        
        for tag_info in TAGS_TO_CREATE:
            tag_name = tag_info["name"].lower()
            
            if tag_name not in existing_tag_names:
                new_tag = discord.ForumTag(
                    name=tag_info["name"],
                    emoji=tag_info.get("emoji")
                )
                new_tags.append(new_tag)
                tags_to_add.append(tag_info["name"])
        
        if new_tags:
            try:
                current_tags = list(forum_channel.available_tags)
                updated_tags = current_tags + new_tags
                
                await forum_channel.edit(available_tags=updated_tags)
                await interaction.followup.send(f"✅ Created {len(new_tags)} new tags: {', '.join(tags_to_add)}")
                
            except Exception as e:
                await interaction.followup.send(f"❌ Error creating tags: {e}")
        else:
            await interaction.followup.send("ℹ️ All tags already exist")

    async def list_available_tags(self, interaction):
        guild = self.get_guild(GUILD_ID)
        forum_channel = guild.get_channel(FORUM_CHANNEL_ID)
        
        response = f"📋 **Available tags in '{forum_channel.name}':**\n\n"
        
        response += "**Location/Type Tags:**\n"
        for tag in forum_channel.available_tags:
            if tag.name in ["settlement", "fortress", "landmark", "border", "trade-hub", "sacred-site"]:
                emoji_str = f"{tag.emoji} " if tag.emoji else ""
                response += f"• {emoji_str}`{tag.name}`\n"
        
        response += "\n**Nation Tags:**\n"
        for tag in forum_channel.available_tags:
            if tag.name in ["armada", "hilltop", "jesthaen", "polaris", "voldaen", "neutral", "multi-nation"]:
                emoji_str = f"{tag.emoji} " if tag.emoji else ""
                response += f"• {emoji_str}`{tag.name}`\n"
        
        response += "\n**Character/NPC Tags:**\n"
        for tag in forum_channel.available_tags:
            if tag.name == "npc":
                emoji_str = f"{tag.emoji} " if tag.emoji else ""
                response += f"• {emoji_str}`{tag.name}`\n"
        
        await interaction.followup.send(response)

    def get_tag_objects(self, forum_channel, tag_names):
        """Convert tag names to tag objects"""
        tag_objects = []
        
        for tag_name in tag_names:
            for available_tag in forum_channel.available_tags:
                if available_tag.name.lower() == tag_name.lower():
                    tag_objects.append(available_tag)
                    break
        
        return tag_objects

    async def create_forum_posts(self, interaction):
        guild = self.get_guild(GUILD_ID)
        if not guild:
            await interaction.followup.send("❌ Could not find server!")
            return

        forum_channel = guild.get_channel(FORUM_CHANNEL_ID)
        if not forum_channel:
            await interaction.followup.send("❌ Could not find forum channel!")
            return

        successful_posts = 0
        failed_posts = 0

        for i, post_data in enumerate(posts_data):
            try:
                tags_to_apply = []
                if "tags" in post_data and post_data["tags"]:
                    tags_to_apply = self.get_tag_objects(forum_channel, post_data["tags"])

                thread = await forum_channel.create_thread(
                    name=post_data["title"],
                    content=post_data["content"],
                    applied_tags=tags_to_apply
                )
                
                successful_posts += 1
                
                # Progress update every 10 posts
                if (i + 1) % 10 == 0:
                    await interaction.followup.send(f"⏳ Progress: {i + 1}/{len(posts_data)} posts created...")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                failed_posts += 1
                print(f"❌ Error creating post {i+1}: {e}")

        # Final summary
        if failed_posts == 0:
            await interaction.followup.send(f"🎉 Successfully created all {successful_posts} forum posts!")
        else:
            await interaction.followup.send(f"📊 Finished! Created {successful_posts} posts, {failed_posts} failed.")

    async def delete_bot_posts(self, interaction):
        guild = self.get_guild(GUILD_ID)
        if not guild:
            await interaction.followup.send("❌ Could not find server!")
            return

        forum_channel = guild.get_channel(FORUM_CHANNEL_ID)
        if not forum_channel:
            await interaction.followup.send("❌ Could not find forum channel!")
            return

        # Get all threads in the forum
        threads = []
        async for thread in forum_channel.archived_threads(limit=None):
            threads.append(thread)
        
        for thread in forum_channel.threads:
            threads.append(thread)

        # Filter threads created by this bot
        bot_threads = [thread for thread in threads if thread.owner_id == self.user.id]

        if not bot_threads:
            await interaction.followup.send("ℹ️ No bot-created posts found to delete.")
            return

        # Create confirmation view with buttons
        view = ConfirmDeleteView(bot_threads, self, interaction.user)
        await interaction.followup.send(
            f"⚠️ **Found {len(bot_threads)} posts created by this bot.**\n"
            f"Are you sure you want to delete them all?",
            view=view
        )

class ConfirmDeleteView(discord.ui.View):
    def __init__(self, bot_threads, bot, original_user):
        super().__init__(timeout=30)
        self.bot_threads = bot_threads
        self.bot = bot
        self.original_user = original_user

    @discord.ui.button(label='Confirm Delete', style=discord.ButtonStyle.danger, emoji='🗑️')
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.original_user:
            await interaction.response.send_message("❌ Only the person who ran the command can confirm.", ephemeral=True)
            return

        await interaction.response.send_message(f"🗑️ Deleting {len(self.bot_threads)} bot-created posts...")
        
        deleted_count = 0
        failed_count = 0

        for i, thread in enumerate(self.bot_threads):
            try:
                await thread.delete()
                deleted_count += 1
                
                if (i + 1) % 10 == 0:
                    await interaction.followup.send(f"⏳ Progress: {i + 1}/{len(self.bot_threads)} posts deleted...")
                
                await asyncio.sleep(0.5)
                
            except Exception as e:
                failed_count += 1
                print(f"❌ Error deleting thread {thread.name}: {e}")

        # Final summary
        if failed_count == 0:
            await interaction.followup.send(f"✅ Successfully deleted all {deleted_count} bot-created posts!")
        else:
            await interaction.followup.send(f"📊 Finished! Deleted {deleted_count} posts, {failed_count} failed.")

        # Disable the view
        self.clear_items()

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.secondary, emoji='❌')
    async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.original_user:
            await interaction.response.send_message("❌ Only the person who ran the command can cancel.", ephemeral=True)
            return

        await interaction.response.send_message("❌ Deletion cancelled.")
        self.clear_items()

    async def on_timeout(self):
        self.clear_items()

# Run the bot
bot = ForumBot()
print("🤖 Starting slash command forum bot...")
bot.run(TOKEN)