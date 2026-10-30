# BusBidderSpain

## How to run:
conda env create -f env.yml <br/>
conda activate busbidder <br/>
python -m pip install -e . <br/>
python data_generator.py <br/>
python main.py <br/>

Compare the predefined traveller profiles directly: <br/>
python main.py --compare <br/>

Run the unit tests<br/>
python -m unittest tests -v <br/>

## The project structure:
BusBidder-Spain/<br/>
│<br/>
├── main.py<br/>
├── data_generator.py<br/>
├── tests.py<br/>
├── pyproject.toml<br/>
├── README.md<br/>
│<br/>
├── src/<br/>
│   └── busbidder/<br/>
│       ├── __init__.py<br/>
│       ├── models.py<br/>
│       ├── market.py<br/>
│       └── booking.py<br/>
│<br/>
├── data/<br/>
│   ├── companies.csv<br/>
│   ├── destinations.csv<br/>
│   ├── offers.csv<br/>
│   └── profiles.json<br/>
│<br/>
├── logs/<br/>
└── output/<br/>
