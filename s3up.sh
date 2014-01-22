#! /usr/bin/env bash
# arguments == tests we want to upload
# to upload everything:  ls static/report/ | xargs ./s3up.sh

for var in "$@"
do
	for file in `ls static/report/$var/*.jpeg`
	do
		#echo "s3cmd put $file s3://wikitoy/$file --acl-public"
		s3cmd put $file s3://wikitoy/$file --acl-public
	done
done