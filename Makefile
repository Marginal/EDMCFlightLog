all:
	rm -f EDMCFlightLog.zip
	cd ..; zip EDMCFlightLog/EDMCFlightLog.zip EDMCFlightLog/README.md EDMCFlightLog/load.py
