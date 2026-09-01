import csv

tags = set()
with open('output/top_100_pre_filtered.csv', 'r') as file:
    csvFile = csv.DictReader(file)
    for row in csvFile:
        tags_weird = row['tags'].removeprefix("['").removesuffix("']").split("', '")
        for tag in tags_weird:
            tags.add(tag)

tags = sorted(tags)
print(tags)