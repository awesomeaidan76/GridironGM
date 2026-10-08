"""names.py — name, college and coach pools for generated people."""
import random

FIRST_NAMES = [
    "Aaron", "Adrian", "Aiden", "Alex", "Andre", "Andrew", "Anthony", "Antonio",
    "Austin", "Bailey", "Beau", "Ben", "Blake", "Bo", "Brad", "Brandon",
    "Brendan", "Brett", "Brian", "Brock", "Bryce", "Byron", "Caleb", "Calvin",
    "Cam", "Cameron", "Carlos", "Carson", "Casey", "Cedric", "Chad", "Chase",
    "Chris", "Christian", "Clay", "Cody", "Colby", "Cole", "Colton", "Connor",
    "Cooper", "Corey", "Craig", "Curtis", "Dak", "Dalton", "Damien", "Damon",
    "Dan", "Dante", "Darius", "Darnell", "Darren", "Davante", "David", "Dawson",
    "Deandre", "Demarcus", "Deon", "Derek", "Derrick", "Desmond", "Devin",
    "Devon", "Dexter", "Dion", "Dominic", "Donovan", "Drew", "Dwayne", "Dylan",
    "Earl", "Eddie", "Elijah", "Eli", "Emmanuel", "Eric", "Ethan", "Evan",
    "Felix", "Frank", "Gabe", "Garrett", "Gavin", "Gerald", "Grant", "Greg",
    "Hayden", "Hunter", "Ian", "Isaac", "Isaiah", "Jack", "Jackson", "Jacob",
    "Jake", "Jalen", "Jamal", "Jamar", "James", "Jamie", "Jared", "Jarvis",
    "Jason", "Javon", "Jaxon", "Jay", "Jaylen", "Jeff", "Jeremiah", "Jeremy",
    "Jerome", "Jesse", "Joe", "Joel", "John", "Jonah", "Jordan", "Jose",
    "Josh", "Josiah", "Juan", "Julian", "Justin", "Kade", "Kaleb", "Kareem",
    "Keenan", "Keith", "Kelvin", "Kendall", "Kenny", "Kevin", "Khalil", "Kirk",
    "Kobe", "Kyle", "Kyler", "Lamar", "Lance", "Landon", "Larry", "Leon",
    "Levi", "Liam", "Logan", "Lorenzo", "Lucas", "Luke", "Malcolm", "Malik",
    "Marcus", "Mario", "Mark", "Marquise", "Marshall", "Martin", "Mason",
    "Matt", "Maurice", "Max", "Micah", "Michael", "Miles", "Mitchell", "Montez",
    "Nate", "Nathan", "Nick", "Noah", "Omar", "Oscar", "Owen", "Parker",
    "Patrick", "Paul", "Peyton", "Preston", "Quentin", "Quincy", "Raheem",
    "Ray", "Reggie", "Ricky", "Riley", "Rob", "Rodney", "Roman", "Ronnie",
    "Russell", "Ryan", "Sam", "Sean", "Seth", "Shane", "Shawn", "Spencer",
    "Stefon", "Sterling", "Steve", "Taylor", "Terrell", "Terrance", "Theo",
    "Thomas", "Tim", "Todd", "Tony", "Travis", "Trent", "Trevor", "Trey",
    "Tristan", "Troy", "Tucker", "Ty", "Tyler", "Tyreek", "Tyrone", "Tyson",
    "Victor", "Vince", "Wade", "Walter", "Warren", "Wesley", "Will", "Xavier",
    "Zach", "Zane", "Zion",
]

LAST_NAMES = [
    "Adams", "Allen", "Alexander", "Anderson", "Armstrong", "Atkins", "Austin",
    "Bailey", "Baker", "Banks", "Barnes", "Barrett", "Bates", "Bell", "Bennett",
    "Black", "Blackwell", "Boone", "Bowers", "Bradley", "Brady", "Brooks",
    "Brown", "Bryant", "Burke", "Burns", "Butler", "Caldwell", "Campbell",
    "Carr", "Carter", "Chambers", "Chandler", "Chapman", "Clark", "Clay",
    "Cobb", "Coleman", "Collins", "Conner", "Cook", "Cooper", "Cox", "Crawford",
    "Cross", "Cunningham", "Daniels", "Davidson", "Davis", "Dawson", "Dean",
    "Dixon", "Douglas", "Drake", "Duncan", "Dunn", "Edwards", "Elliott", "Ellis",
    "Evans", "Ferguson", "Fields", "Fisher", "Fleming", "Fletcher", "Ford",
    "Foster", "Fowler", "Franklin", "Freeman", "Fuller", "Gaines", "Gardner",
    "Garrett", "Gibson", "Gilbert", "Gordon", "Graham", "Grant", "Graves",
    "Gray", "Green", "Griffin", "Hall", "Hamilton", "Hampton", "Hardy",
    "Harper", "Harris", "Harrison", "Hart", "Hawkins", "Hayes", "Henderson",
    "Henry", "Hill", "Hines", "Holland", "Holmes", "Hopkins", "Howard",
    "Hudson", "Hughes", "Hunt", "Hunter", "Jackson", "James", "Jefferson",
    "Jenkins", "Johnson", "Jones", "Jordan", "Kelly", "Kennedy", "King",
    "Knight", "Lambert", "Lane", "Lawrence", "Lawson", "Lee", "Lewis", "Lockett",
    "Long", "Lyons", "Mack", "Marshall", "Martin", "Mason", "Matthews", "Maxwell",
    "Mayfield", "McCoy", "McDaniel", "McKinney", "Meyers", "Miller", "Mills",
    "Mitchell", "Moore", "Morgan", "Morris", "Moss", "Murphy", "Murray",
    "Nelson", "Newton", "Nichols", "Norman", "Owens", "Palmer", "Parker",
    "Patterson", "Payne", "Pearson", "Perkins", "Perry", "Peters", "Phillips",
    "Pierce", "Porter", "Powell", "Price", "Pryor", "Ramsey", "Randall",
    "Reed", "Reese", "Reynolds", "Rhodes", "Rice", "Richards", "Richardson",
    "Riley", "Rivers", "Roberts", "Robinson", "Rogers", "Ross", "Russell",
    "Sanders", "Saunders", "Scott", "Sharpe", "Shaw", "Simmons", "Simpson",
    "Sims", "Smith", "Snyder", "Spencer", "Stafford", "Stanley", "Stephens",
    "Stevens", "Stewart", "Stone", "Sullivan", "Sutton", "Taylor", "Terry",
    "Thomas", "Thompson", "Tucker", "Turner", "Vaughn", "Wagner", "Walker",
    "Wallace", "Walsh", "Ward", "Warner", "Warren", "Washington", "Watkins",
    "Watson", "Watts", "Webb", "Weeks", "Wells", "West", "Wheeler", "White",
    "Whitfield", "Wilkins", "Williams", "Willis", "Wilson", "Winston", "Wood",
    "Woods", "Wright", "Young",
]

COLLEGES = [
    "Alabama", "Georgia", "Ohio State", "Michigan", "LSU", "Clemson", "Texas",
    "Oklahoma", "USC", "Notre Dame", "Penn State", "Florida", "Florida State",
    "Miami", "Oregon", "Washington", "Auburn", "Tennessee", "Texas A&M",
    "Wisconsin", "Iowa", "Utah", "TCU", "Baylor", "Ole Miss", "Mississippi St.",
    "Arkansas", "Kentucky", "South Carolina", "Missouri", "Nebraska",
    "Minnesota", "Michigan State", "Purdue", "Illinois", "Northwestern",
    "Maryland", "Rutgers", "Pittsburgh", "Virginia Tech", "Louisville",
    "North Carolina", "NC State", "Duke", "Wake Forest", "Boston College",
    "Syracuse", "Stanford", "California", "UCLA", "Arizona", "Arizona State",
    "Colorado", "Oregon State", "Washington State", "Kansas State",
    "Oklahoma State", "Iowa State", "West Virginia", "Texas Tech", "Houston",
    "Cincinnati", "UCF", "BYU", "Boise State", "San Diego State",
    "Fresno State", "Memphis", "Tulane", "SMU", "Toledo", "Western Michigan",
    "Central Michigan", "Northern Illinois", "Appalachian St.", "Coastal Carolina",
    "Marshall", "Liberty", "Air Force", "Navy", "Army", "North Dakota State",
    "South Dakota State", "Montana", "Jackson State", "Grambling", "Howard",
    "Delaware", "Villanova", "James Madison", "Sam Houston", "Furman",
]

HOMETOWNS = [
    "Houston, TX", "Dallas, TX", "Atlanta, GA", "Miami, FL", "Tampa, FL",
    "Jacksonville, FL", "Los Angeles, CA", "San Diego, CA", "Oakland, CA",
    "Phoenix, AZ", "New Orleans, LA", "Baton Rouge, LA", "Birmingham, AL",
    "Mobile, AL", "Memphis, TN", "Nashville, TN", "Columbus, OH", "Cleveland, OH",
    "Cincinnati, OH", "Detroit, MI", "Chicago, IL", "St. Louis, MO",
    "Kansas City, MO", "Philadelphia, PA", "Pittsburgh, PA", "Baltimore, MD",
    "Washington, DC", "Charlotte, NC", "Raleigh, NC", "Columbia, SC",
    "Richmond, VA", "Newark, NJ", "Brooklyn, NY", "Boston, MA", "Seattle, WA",
    "Portland, OR", "Denver, CO", "Las Vegas, NV", "Salt Lake City, UT",
    "Oklahoma City, OK", "Tulsa, OK", "Little Rock, AR", "Jackson, MS",
    "Omaha, NE", "Des Moines, IA", "Milwaukee, WI", "Minneapolis, MN",
    "Indianapolis, IN", "Louisville, KY", "Honolulu, HI", "Toronto, ON",
]


def random_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def random_college():
    # Bigger programmes produce more players
    if random.random() < 0.55:
        return random.choice(COLLEGES[:30])
    return random.choice(COLLEGES)


def random_hometown():
    return random.choice(HOMETOWNS)
