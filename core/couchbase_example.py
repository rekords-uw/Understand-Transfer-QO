import logging
import sys
import couchbase.subdocument as SD

from couchbase.cluster import Cluster, PasswordAuthenticator

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

# open cluster and authenticate as Cluster Admin
cluster = Cluster('couchbase://127.0.0.1:8091')
cluster.authenticate(PasswordAuthenticator('couchbase', 'couchbase'))

# open travel-sample bucket
bucket = cluster.open_bucket('travel-sample')

# Add key-value pairs to hotel_10138, representing traveller-Ids and associated discount percentages
bucket.mutate_in('hotel_10138',
                SD.upsert('discounts.jsmith123', '20', xattr=True, create_parents=True),
                SD.upsert('discounts.pjones356', '30', xattr=True, create_parents=True),
                # The following lines, "insert" and "remove", simply demonstrate insertion and
                # removal of the same path and value
                SD.insert('discounts.jbrown789', '25', xattr=True, create_parents=True),
                SD.remove('discounts.jbrown789', xattr=True)
                )

# Add key - value pairs to hotel_10142, again representing traveller - Ids and associated discount percentages
bucket.mutate_in('hotel_10142',
                SD.upsert('discounts.jsmith123', '15', xattr=True, create_parents=True),
                SD.upsert('discounts.pjones356', '10', xattr=True, create_parents=True)
                )

# Create a user and assign roles. This user will search for their available discounts.
manager = cluster.cluster_manager()
                manager.user_upsert('jsmith123', 'jsmith123pwd', [
                # Roles required for the reading of data from the bucket
                ('data_reader', 'travel-sample'),
                ('query_select', 'travel-sample'),

                # Roles required for the writing of data into the bucket
                ('data_writer', 'travel-sample'),
                ('query_insert', 'travel-sample'),
                ('query_delete', 'travel-sample'),

                # Role required for the creation of indexes on the bucket
                ('query_manage_index', 'travel-sample')
                ], 'John Smith')

# reconnect using new user
cluster = Cluster('couchbase://10.112.170.101')
cluster.authenticate(PasswordAuthenticator('jsmith123', 'jsmith123pwd'))

# must have at least one open bucket to submit cluster query
bucket = cluster.open_bucket('travel-sample')

# Perform a N1QL Query to return document IDs from the bucket. These IDs will be
# used to reference each document in turn, and check for extended attributes
# corresponding to discounts.
result = cluster.n1ql_query('SELECT id, meta(`travel-sample`).id AS docID FROM `travel-sample`')
results = ''

for row in result:
    # get row document ID
    docID = row['docID']

    # Determine whether a hotel-discount has been applied to this user.
    r = bucket.lookup_in(docID, SD.exists('discounts.jsmith123', xattr=True))
    if r.exists('discounts.jsmith123'):

        # If so, get the discount-percentage.
        r = bucket.lookup_in(docID, SD.get('discounts.jsmith123', xattr=True))
        discount = r['discounts.jsmith123']

        # If the percentage - value is greater than 15, include the document in the
        # results to be returned.
        results = '%s\n%s - %s' % (results, discount, docID)

print("Results returned are: %s" % results)