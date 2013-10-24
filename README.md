# Balance

A simple tool to keep track of who owes who among a group of friends/co-workers.

## Installation

1. Fill in the right settings for the database
   connection in the settings.py file. Alternatively,
   one could use a SQLite database and change the
   connection creation and script exit functions to
   connect to the SQLite database and to commit before exit.
2. Run the `database_schema.sql` file (source it from mysql shell etc.) to
   create the empty tables.
3. Change the server's config file to use some authentication
   or pass the username in some other way  to the script.
4. Set the `admin` user in the `settings.py` file.


## Usage

To start off, login as "admin" and add users to the system
by issuing the command `add user1 user2 ...`.

The man page and other usage examples are given on the webpage itself.

## License

Please acknowledge any use of this software and let me know when using.

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  For the terms of the license, see <http://www.gnu.org/licenses/>.
