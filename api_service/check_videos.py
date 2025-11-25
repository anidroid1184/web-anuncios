import pandas as pd
import json

csv_path = r"app\processors\datasets\saved_datasets\facebook\bfMXWLphPQcDmBsrz\bfMXWLphPQcDmBsrz.csv"
df = pd.read_csv(csv_path)

video_count = 0
ads_with_videos = []

for _, row in df.iterrows():
    ad_id = str(row.get('ad_archive_id'))
    snapshot_str = str(row.get('snapshot', '{}'))

    try:
        snapshot = eval(snapshot_str)
        videos = snapshot.get('videos', [])
        if videos:
            video_count += 1
            ads_with_videos.append({
                'ad_id': ad_id,
                'num_videos': len(videos),
                'video_url': videos[0].get('video_hd_url', 'N/A') if videos else 'N/A'
            })
    except:
        pass

print(f"Anuncios con videos: {video_count} de {len(df)}")
print(f"\nPrimeros 5 anuncios con videos:")
for i, ad in enumerate(ads_with_videos[:5]):
    print(f"  {i+1}. ID: {ad['ad_id']} - Videos: {ad['num_videos']}")
    print(f"     URL: {ad['video_url'][:80]}...")
