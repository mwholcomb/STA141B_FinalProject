#!/usr/bin/env python
# coding: utf-8

# In[1]:


## Read in CSV Files Needed ##
import pandas as pd

Arena_Info = pd.read_csv("data/Arena_Info.csv")

Venue_Events = {}

for arena in Arena_Info['Arena']:
    Venue_Events[arena] = pd.read_csv(f'data/{arena}.csv')
    
NBA_Arenas = pd.read_csv("data/NBA_Arenas.csv")


# In[2]:


def Get_Arena_Info(team_name):
    '''
    Returns a dictionary of the relevant information for a given team.
    
    Parameters:
        team_name (string): The name of the team
        
    Returns:
        dictionary: A dictionary containing relevant information
    '''
    
    Team_Info = Arena_Info[Arena_Info['Team'] == team_name]
    
    info = {
        'Events': Venue_Events[Team_Info['Arena'].iloc[0]],
        'Star Player': Team_Info['Player'].iloc[0],
        'Stats': Team_Info[['PPG', 'RPG', 'APG', 'PIE']],
        'Star Player YT Views': Team_Info['Views'].iloc[0],
        'Avg. Ticket Prices': Team_Info[['Home Minimum', 'Home Maximum', 'Away Minimum', 'Away Maximum']],
        'County': Team_Info['County'].iloc[0],
        'County GDP': Team_Info['County GDP (Billions)'].iloc[0],
        'County Income per Capita': Team_Info['County Income Per Capita'].iloc[0],
        'Longitude': NBA_Arenas[NBA_Arenas['Home Team'] == team_name]['longitude'].iloc[0],
        'Latitude': NBA_Arenas[NBA_Arenas['Home Team'] == team_name]['latitude'].iloc[0]
    }
    
    return info


# In[3]:


Arena_Dictionary = {Team: Get_Arena_Info(Team) for Team in Arena_Info['Team']}


# In[4]:


import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from shapely.geometry import Point

gdf = gpd.read_file('US_State/cb_2018_us_state_500k.shp')

# Remove any states we are not going to be using
Main_States = gdf[~gdf['STUSPS'].isin(['AK', 'PR', 'HI', 'AS', 'MP', 'GU', 'VI'])]


# In[5]:


import textwrap
from io import BytesIO

# Initialize figure
def Team_Loc_PNG(team_name):
    '''
    Given a team name, returns PNG data of an image showing the map of where the arena
    for that team is located.
    
    Parameters:
        team_name (string): The team name
        
    Returns:
        bytes: PNG data from the buffer
    '''
    fig, ax = plt.subplots(figsize=(10,10))
    Main_States.plot(ax=ax, color='lightblue', edgecolor='gray')

    Arena_df = NBA_Arenas[NBA_Arenas['Home Team'] == team_name]
    lon = Arena_df['longitude'].iloc[0]
    lat = Arena_df['latitude'].iloc[0]
    arena_name = Arena_df['Arena'].iloc[0]
    
    # Plot the point with the relevant colored point.
    ax.plot(lon, lat, marker = 'o', color = "red", markersize = 10)
    ax.text(lon, lat+0.5, arena_name, fontsize = 10, ha = 'center', fontweight = 'bold')
    plt.title(f'{arena_name}, the Home of the {team_name}', fontsize = 10, fontweight = 'bold')

    city = Arena_df['Location'].iloc[0]
    county = Arena_Dictionary[team_name]['County']
    gdp = Arena_Dictionary[team_name]['County GDP']
    income = Arena_Dictionary[team_name]['County Income per Capita']
    
    # Remove Axes
    ax.set_xticks([])
    ax.set_yticks([])
    
    # Adding a customizable text box in the lower left corner
    custom_text = f'''
    City: {city} 
    County: {county} 
    County GDP (Billions of $): {gdp} 
    County Income per Capita ($): {income}'''
    custom_text = textwrap.dedent(custom_text)
    # Position for the text: xmin, ymin of the axes
    ax.text(0.01, 0.01, custom_text, transform=ax.transAxes, fontsize = 10, 
            verticalalignment='bottom', horizontalalignment='left', fontweight='bold')

    plt.tight_layout()
    
    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    buffer.seek(0)
    
    plt.close(fig)
    
    return buffer.getvalue()


# In[6]:


from dash import Dash, html, dcc, dash_table, callback, Output, Input
import plotly.express as px
import base64

app = Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H1(children='NBA Team Arenas', style={'textAlign': 'center'}), # The header for the webpage
    dcc.Dropdown(id='dropdown-selection', # The dropdown menu
                 options=[{'label': team, 'value': team} for team in Arena_Info['Team']], 
                 value='Atlanta Hawks'),
    html.Div(id='star-player-display'), # The name of the star player
    dash_table.DataTable(id='table-content'), # The table containing the star player's stats
    dcc.Graph(id='team-wins-plot'), # The graph containing the ticket pricing compared to other teams
    html.Div(html.Img(id='team-map', 
                      style={'display': 'block', 'margin-left': 'auto', 'margin-right': 'auto'}), 
             style={'text-align': 'center'})

])

@app.callback(
    [Output('star-player-display', 'children'), 
     Output('table-content', 'data'), 
     Output('team-wins-plot', 'figure')],
    [Input('dropdown-selection', 'value')]
)
def update_content(selected_team):
    
    player_name_text = f"Star Player: {Arena_Dictionary[selected_team]['Star Player']}"
    
    # Add a new column to indicate the selected team
    colors = Arena_Info['Team'].apply(lambda x: "blue" if x == selected_team else "red")
    color_discrete_map = {'blue': 'blue', 'red': 'red'}
    
    # Assuming 'Stats' key in Arena_Dictionary[selected_team] gives a DataFrame
    stats_df = Arena_Dictionary[selected_team]['Stats']
    data = stats_df.to_dict('records')
    
    # Create the scatter plot, coloring by the 'Selected' column
    fig = px.scatter(Arena_Info, x='Home Minimum', y='Away Minimum', 
                     color=colors, color_discrete_map=color_discrete_map,
                     title=f"Avg. Minimum Ticket Prices: {selected_team} Price (Blue) vs Other Teams (Red)")
    
    # Optionally, adjust legend and color scale visibility
    fig.update_layout(
        showlegend=False,
        xaxis_title="Average Minimum Home Game Ticket Price",
        yaxis_title="Average Minimum Away Game Ticket Price"
    )
    fig.update_traces(marker=dict(size=12)) # Adjust marker size
    
    return player_name_text, data, fig

    
@app.callback(
    Output('team-map', 'src'),
    [Input('dropdown-selection', 'value')]
)

def update_team_map(selected_team):
    # Assume Team_Loc_PNG returns PNG data for the selected team
    png_data = Team_Loc_PNG(selected_team)
    
    # Encode the PNG data to base64
    data = base64.b64encode(png_data).decode('utf-8')
    
    # Return the image in a format that html.Img can use
    return f'data:image/png;base64,{data}'


if __name__ == '__main__':
    app.run_server(debug=True)

