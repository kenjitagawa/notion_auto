from notion.client import NotionClient
import telebot
from github import Github

import dotenv
import os
import requests
from bs4 import BeautifulSoup

from flask import Flask
import time

from threading import Thread

dotenv.load_dotenv()

# Idea
# The idea of this project is to implement the Notion api to my personal notes and automate the creation
# of links and table items through a Telegram Bot.
# How it Works
# The bot will be added to a group and once a link is send the bot will use regular expressions to read the link
# based on the items
# information contained within the links, the bot will add it to the appropriate table.
#
# Step by step process
# get link from groupchat
# get tags, language
# use requests to get title (only for yt, medium, tds, else title = " ")
# use regex to check the title and the link for a programming language/ possible tags
# if none, tag = " "
# add to table
# message chat when complete
#
#
app = Flask(__name__)
list_urls = []


class Bots:
    def __init__(self, _type, urls_list):
        """On start, the bot will automatically try to add links to Notion. If there are no links,
            it will wait several seconds and retry recursively.
            """

        # Store the URLs
        self.urls = urls_list

        # Create the _type variable
        self._type = _type

        # Connect to Notion
        token = os.getenv(f"TOKEN")
        self.client = NotionClient(token_v2=token)
        self.link = os.getenv("LINK")

        # Connect to GitHub
        # Loading the github token & connecting to GH bot
        gh_token = os.getenv("GITHUB_TOKEN")
        self.GH = Github(gh_token)

        # Connecting bots
        tg_token = os.getenv(self._type)
        self.bot = telebot.TeleBot(token=tg_token)

        # Recipient
        self.send_to = os.getenv('SEND_TO')

    @staticmethod
    def back_up(url, new_type=None):
        # This will run if the below mentioned functions fail.
        r = requests.get(url).text
        soup = BeautifulSoup(r, 'lxml')
        title = soup.find('title').text
        language = "None"

        # Preparing for the Notion Class
        return title, language, new_type, url

    def gh(self, url):
        # Get the items
        # information for the named repository.
        title = url.split("/")[-1]
        repository = url.split('/')[-2] + "/" + title
        language = self.GH.get_repo(repository).language
        new_type = "Github"
        items = (title, language, new_type, url)

        # Preparing for the Notion Class
        return tuple(items)

    @staticmethod
    def yt(url):
        # Get the items
        # information of the youtube video.
        r = requests.get(url).text
        soup = BeautifulSoup(r, 'lxml')
        title = soup.find('title').text.replace(' - YouTube', '')
        language = 'None'
        new_type = 'Video'
        items = (title, language, new_type, url)

        # Preparing for the Notion Class
        return tuple(items)

    @staticmethod
    def tds(url):
        # Finding the items
        # information of the Medium/Towards Data Science articles.
        r = requests.get(url).text
        soup = BeautifulSoup(r, 'lxml')
        # Getting the title
        title = soup.find('title').text
        # Getting all of the <a> tags from the HTML
        list_a = soup.findAll('a', {'class': ['cd', 'b', 'ce', 'qm', 'cg', 'qn', 'qo', 'gr', 's', 'ln']})
        prog = ['python', 'java', 'javascript', 'cpp', 'c++']
        languages = [lang for lang in prog if lang in [_.text.lower() for _ in list_a]]

        new_type = 'Article'
        items = (title, languages[0], new_type, url)

        # Preparing for the Notion Class
        return tuple(items)


class VideoBot(Bots):

    def run(self):

        print('|Starting Videos Bot|')

        @self.bot.message_handler(func=(lambda message: True))
        def _reply(message):
            time.sleep(5)

            # Check every message to see if any of the values in white list are in it, and then
            # get sorted out based on the "if" statements.
            if 'http' in message.text:
                # Allowed links
                white_list = ['github.com', 'youtu.be', 'youtube.com']

                # Returns True if any of the values in white list are in the text
                if any([True for value in white_list if value in message.text]):
                    value = [value for value in white_list if value in message.text]

                    if value[0] == 'youtu.be' or value[0] == 'youtube.com':
                        try:
                            # Main function for Videos
                            link = self.yt(message.text)
                            self.urls.append(link)

                        except Exception as e:
                            print(e)
                            # Calling the back up in case of failure
                            link = self.back_up(message.text, new_type='Article')
                            self.urls.append(link)

                        finally:
                            self.bot.send_message(self.send_to,
                                                  f'Adding a link to Notion ASAP...',
                                                  disable_web_page_preview=True)

                    if value[0] == 'github.com':
                        try:
                            # Main function for Repositories
                            link = self.gh(message.text)
                            self.urls.append(link)

                        except Exception as e:
                            print(e)
                            # Calling the back up in case of failure
                            link = self.back_up(message.text, new_type='Article')
                            self.urls.append(link)

                        finally:
                            self.bot.send_message(self.send_to,
                                                  f'Adding "{self.link[0]}" to Notion ASAP...',
                                                  disable_web_page_preview=True)

                else:
                    time.sleep(1)
                    self.bot.send_message(self.send_to, 'That seems like an article!')

            else:
                time.sleep(1)
                self.bot.send_message(self.send_to, "Hey, Are you there? I think this is for you!")

        self.bot.infinity_polling()


class ArticleBot(Bots):

    def run(self):
        print('|Starting Articles Bot|')

        @self.bot.message_handler(func=lambda message: True)
        def _reply(message):
            time.sleep(5)
            if "http" in message.text:
                # Black list the values below as the bots will be in the
                black_list = ['github.com', 'youtu.be', 'youtube.com']
                if any([True for value in black_list if value in message.text]):
                    # After filtering out values:
                    self.bot.send_message(self.send_to, f'Hey! I will leave that to someone else!')
                    return

                if 'medium.com' in message.text or 'towardsdatascience.com' in message.text:
                    try:
                        # Main function for Articles
                        link = self.tds(message.text)
                        self.urls.append(link)

                    except Exception as e:
                        print(e)
                        # Calling the back up in case of failure
                        link = self.back_up(message.text, new_type='Article')
                        self.urls.append(link)

                    finally:
                        self.bot.send_message(self.send_to,
                                              f'Adding "{self.link[0]}" to Notion ASAP...',
                                              disable_web_page_preview=True)

                else:

                    try:
                        # Calling the back up since this will be for a general case
                        link = self.back_up(message.text, new_type='Article')
                        self.urls.append(link)

                    except Exception as e:
                        print(e)
                        link = ('None', 'None', 'Article', message.text)
                        self.urls.append(link)

                    finally:
                        self.bot.send_message(self.send_to,
                                              f'Adding "{self.link[0]}" to Notion ASAP...',
                                              disable_web_page_preview=True)

            else:
                time.sleep(1)
                # Replying to any other message that isn't http
                self.bot.send_message(self.send_to, 'I think that he isn\'t talking to me...')

        self.bot.infinity_polling()


class WorkingBot(Bots):

    def run(self):
        print('|Starting Working Bot|')

        self.bot.send_message(self.send_to, "Starting to work, don't bother me!")

        @self.bot.message_handler(func=lambda message: True)
        def _reply(message):
            time.sleep(5)
            if 'http' in message.text:

                self.bot.send_dice(self.send_to)

                white_list = ['github.com', 'youtu.be', 'youtube.com']
                if any([True for value in white_list if value in message.text]):
                    self.bot.send_message(self.send_to, 'I will add it to Notion right now ')

                else:
                    self.bot.send_message(self.send_to, 'I will add it to Notion right now!')

                while len(self.urls) != 0:
                    try:
                        for items in self.urls:
                            title, language, new_type, url = items

                            # Add to notion table.
                            page = self.client.get_collection_view(self.link)

                            new_row = page.collection.add_row()
                            new_row.name = title
                            new_row.link = url
                            new_row.type = new_type

                            try:
                                new_row.language = language

                            except Exception as e:
                                print(e)
                                new_row.language = "None"

                            print('|Added to Notion!|')

                            self.urls.remove(items)

                    except Exception as e:
                        return e

                    finally:
                        print('Done')

            else:
                time.sleep(2)
                self.bot.send_message(self.send_to, f"Don't interrupt me {os.getenv('DEV_USERNAME')}!")

        self.bot.infinity_polling()


@app.route('/')
def home():
    return "Hello. I am alive!"


def run():
    app.run(host='0.0.0.0', port=8080)


def keep_alive():
    t = Thread(target=run)
    t.start()


def run_bots():
    # Adding server
    keep_alive()

    # Initializing bots
    b1 = VideoBot('1', list_urls)
    b2 = ArticleBot('2', list_urls)
    b3 = WorkingBot('3', list_urls)

    # Threading
    Thread(target=b1.run).start()
    Thread(target=b2.run).start()
    Thread(target=b3.run).start()


if __name__ == '__main__':
    # app.run(debug=True)
    run_bots()
