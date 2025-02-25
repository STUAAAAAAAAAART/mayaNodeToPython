from datetime import datetime as dt

def timestampMaker() -> str :
	saveTime = dt.now()
	# get timestamp in current day (24h not unix, 0-86399)
	makeSecondsTimestamp = (saveTime.hour*3600) + (saveTime.minute * 60) + saveTime.second
	# get system timezone, UTC offset
	sysTimezone = (saveTime.astimezone().utcoffset().seconds) / 36
	# format system timezone offset to hhmm
	tzHalfHourValue = abs(sysTimezone) % 100 # see if UTC offset has minutes
	if tzHalfHourValue:
		tzHalfHourValue = int(tzHalfHourValue * 0.6) # convert seconds to mm in hhmm
		sysTimezone = int(sysTimezone / 100) * 100 + tzHalfHourValue * (sysTimezone > 0) - tzHalfHourValue * (sysTimezone < 0)
		#           = ------------ hh -------------  --------- +mm if positive ---------   --------- -mm if negative ---------

	sysTimezone = int(sysTimezone)

	if sysTimezone < 0:
		sysTimezone = f"{sysTimezone:05d}"
	else:
		sysTimezone = f"{sysTimezone:04d}"

	# make dateString (utc0.yyyy.mm.dd.sssss)
	return f"{sysTimezone}.{saveTime.year:04}.{saveTime.month:02}.{saveTime.day:02}.{makeSecondsTimestamp:05}"