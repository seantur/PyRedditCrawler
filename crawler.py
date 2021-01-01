import argparse
import json
import logging
import math
from pprint import pprint
import re

import praw
import prawcore

LOGGER = logging.getLogger('CRAWLER')


def get_sidebar_subreddits(crawler, subreddit: str):
    subreddit = subreddit.lower()
    print(subreddit)

    try:
        desc = crawler.subreddit(subreddit).description
        if desc is None:
            desc = ""
        public_desc = crawler.subreddit(subreddit).public_description
        if public_desc is None:
            public_desc = ""

        description = " ".join([desc, public_desc])

    except (prawcore.exceptions.Forbidden,
            prawcore.exceptions.Redirect,
            prawcore.exceptions.BadRequest,
            prawcore.exceptions.NotFound) as e:
        LOGGER.warning(f'{subreddit}: {e}')
        return {subreddit: []}

    # https://github.com/reddit-archive/reddit/blob/753b17407e9a9dca09558526805922de24133d53/r2/r2/models/subreddit.py#L114
    matches = re.findall("\/r\/([a-zA-Z0-9][\w:]{2,20})", description)

    sub_set = set([sub.lower() for sub in matches])
    sub_set.discard(subreddit)

    return {subreddit: sorted(list(sub_set))}


def save_to_json(reddit_dict, path):
    with open(path, 'w') as f:
        json.dump(reddit_dict, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description='scrape subreddit descriptions')
    parser.add_argument('--crawled', help='existing crawler.json', required=False)
    parser.add_argument('--to_visit', help='existing to_visit.json', required=False)
    parser.add_argument('--max_iter', type=int, default=math.inf, required=False)
    parser.add_argument('--checkpoint_iter', type=int, default=10, required=False)
    args = parser.parse_args()

    checkpoint_iter = args.checkpoint_iter
    max_iter = args.max_iter
    if args.crawled is not None:
        with open(args.crawled, 'r') as f:
            reddit_dict = json.load(f)
    else:
        reddit_dict = {}

    if args.to_visit is not None:
        with open(args.to_visit, 'r') as f:
            to_visit = set(json.load(f))
    else:
        to_visit = set(['microfinance'])
 
    n_iter = 0
    crawler = praw.Reddit("crawler")

    while len(to_visit) and n_iter < max_iter:
        subreddit = to_visit.pop()
        sub_dict = get_sidebar_subreddits(crawler, subreddit)

        reddit_dict.update(sub_dict)

        print('-'*10)
        print(f'Iteration: {n_iter}')
        for sub in sub_dict[subreddit]:
            if sub not in reddit_dict and sub not in to_visit:
                to_visit.add(sub)

        print(f'To visit: {len(to_visit)}')
        print(f'Visited: {len(reddit_dict)}')

        if n_iter % checkpoint_iter == 0 and n_iter != 0:
            print('*'*10, 'CHECKPOINTING', '*'*10)
            save_to_json(reddit_dict, 'crawler_checkpoint.json')
            save_to_json(list(to_visit), 'to_visit_checkpoint.json')

        n_iter += 1

    save_to_json(reddit_dict, 'crawler.json')
    save_to_json(list(to_visit), 'to_visit.json')


if __name__ == "__main__":
    main()
