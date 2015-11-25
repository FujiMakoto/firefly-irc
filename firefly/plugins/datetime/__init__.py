import datetime
import logging
import arrow
from firefly import irc, PluginAbstract


class DateTime(PluginAbstract):
    pass

    # @irc.command('now', 'admin')
    # def now(self):
    #     pass


# class Datetime:
#     def __init__(self, plugin):
#         """
#         Initialize a new Datetime instance
#         Args:
#             plugin(src.plugins.Plugin): The plugin instance
#         """
#         # Get the plugin configuration
#         self.plugin  = plugin
#         self.log     = logging.getLogger('nano.plugins.datetime')
#         self.now     = datetime.datetime.now()
#
#     @staticmethod
#     def suffix(day):
#         """
#         Get the English suffix for the specified day of the month
#         Returns:
#             str
#         """
#         return 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
#
#     def day(self):
#         """
#         Get the day of the month
#         Returns:
#             str
#         """
#         self.log.debug('Returning the day')
#         day = self.now.strftime("%-d")
#         return day + self.suffix(int(day))
#
#     def day_of_week(self):
#         """
#         Get the day of the week
#         Returns:
#             str
#         """
#         self.log.debug('Returning the week')
#         return self.now.strftime("%A")
#
#     def month(self):
#         """
#         Get the current month
#         Returns:
#             str
#         """
#         self.log.debug('Returning the month')
#         return self.now.strftime("%B")
#
#     def year(self):
#         """
#         Get the current year
#         Returns:
#             str
#         """
#         self.log.debug('Returning the year')
#         return self.now.strftime("%Y")
#
#     def date(self):
#         """
#         Get the current formatted date
#         Returns:
#             str
#         """
#         self.log.debug('Returning the formatted date')
#         return "{month} {day}, {year}".format(month=self.month(), day=self.day(), year=self.year())
#
#     def time(self, timezone=False):
#         """
#         Get the current time in the format HH:MM AM/PM
#         Args:
#             timezone(bool): Include the timezone at the end of the response
#         Returns:
#             str
#         """
#         time = self.now.strftime("%-I:%M %p")
#
#         # Are we suffixing the time zone to our result?
#         if timezone:
#             time = self.now.strftime("%-I:%M %p") + " " + self.now.strftime("%Z")
#             time = time.rstrip(" ")
#
#         self.log.debug('Returning the time')
#         return time
#
#     def how_long_ago(self, epoch):
#         """
#         Get the difference from the provided epoch to now in days or years
#         Args:
#             epoch(int or str): The Unix timestamp to subtract from
#         Returns:
#             str
#         """
#         now_epoch = self.now.timestamp()
#         epoch     = int(epoch)
#
#         # Is our provided epoch in the future?
#         if epoch > now_epoch:
#             return "0 days"
#
#         difference_epoch = now_epoch - epoch
#
#         # Not a full day?
#         if difference_epoch < 86400:
#             return "0 days"
#
#         # How many days ago?
#         difference_days = difference_epoch / 86400
#
#         # Was this more than a year (365 days) ago, and if so, how many years is it?
#         if difference_days >= 365:
#             difference_years = difference_days / 365
#             difference = int(difference_years)
#
#             # Singular or plural?
#             if difference == 1:
#                 difference = "1 year"
#             else:
#                 difference = str(difference) + " years"
#         else:
#             difference = int(difference_days)
#
#             # Singular or plural?
#             if difference == 1:
#                 difference = "1 day"
#             else:
#                 difference = str(difference) + " days"
#
#         self.log.debug('Returning a time difference')
#         return difference
