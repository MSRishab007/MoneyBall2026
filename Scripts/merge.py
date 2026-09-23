import pandas as pd
import unicodedata
import difflib

# 1. Load the files
excel_path = "Scripts\Players_List_Moneyball26.xlsx"
csv_path = "Scripts\Fifa 23 Players Data.csv"

df_auction = pd.read_excel(excel_path)
df_official = pd.read_csv(csv_path, low_memory=False)

# 2. Function to remove accents and special characters (e.g., Modrić -> Modric)
def normalize_text(text):
    if pd.isna(text): return ""
    text = str(text).strip().lower()
    return ''.join(c for c in unicodedata.normalize('NFKD', text) if unicodedata.category(c) != 'Mn')

# Normalize the target names in the official dataset
df_official['norm_known_as'] = df_official['Known As'].apply(normalize_text)
df_official['norm_full_name'] = df_official['Full Name'].apply(normalize_text)

# Create a combined pool of all official names for the fuzzy matcher
official_name_pool = list(set(df_official['norm_known_as'].tolist() + df_official['norm_full_name'].tolist()))

# 3. Create a matching function
def get_best_match(auction_name):
    clean_name = normalize_text(auction_name)
    
    # Check for an exact normalized match first
    if clean_name in df_official['norm_known_as'].values:
        return df_official[df_official['norm_known_as'] == clean_name].iloc[0]
    if clean_name in df_official['norm_full_name'].values:
        return df_official[df_official['norm_full_name'] == clean_name].iloc[0]
    
    # If no exact match, use fuzzy matching (requires at least 70% similarity)
    close_matches = difflib.get_close_matches(clean_name, official_name_pool, n=1, cutoff=0.70)
    
    if close_matches:
        best_string = close_matches[0]
        # Retrieve the row that matches this string
        match_row = df_official[(df_official['norm_known_as'] == best_string) | 
                                (df_official['norm_full_name'] == best_string)]
        if not match_row.empty:
            return match_row.iloc[0]
            
    # Return empty series if absolutely nothing is found
    return pd.Series(dtype='float64')

# 4. Apply the matcher to the entire auction list
print("Running fuzzy matcher. This may take 10-20 seconds...")
matched_data = df_auction['Player_Name'].apply(get_best_match)

# 5. Combine the original auction data with the new matched attributes
master_df = pd.concat([df_auction, matched_data], axis=1)

# Drop temporary columns if they got merged over
if 'norm_known_as' in master_df.columns:
    master_df.drop(columns=['norm_known_as', 'norm_full_name'], inplace=True)

# 6. Audit the final unmatched players
unmatched_players = master_df[master_df['Known As'].isna()]
print(f"\nTotal Unmatched Players remaining: {len(unmatched_players)}")

if len(unmatched_players) > 0:
    print("--- List of Unmatched Players (Manual Fix Required) ---")
    for index, row in unmatched_players.iterrows():
        print(f"- {row['Player_Name']}")

# 7. Export the final sheet
output_file = 'Master_Auction_List_FIFA23_FuzzyMatched.xlsx'
master_df.to_excel(output_file, index=False)
print(f"\nSuccessfully created new sheet: {output_file}")