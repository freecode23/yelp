import math
import numpy
from etl import similarity
from tripadvisor.fourcity import extractor

__author__ = 'fpena'


def build_user_clusters(reviews, significant_criteria_ranges=None):
    """
    Builds a series of clusters for users according to their significant
    criteria. Users that have exactly the same significant criteria will belong
    to the same cluster.

    :param reviews: the list of reviews
    :return: a dictionary where all the keys are the cluster names and the
    values for those keys are list of users that belong to that cluster
    """

    user_list = extractor.get_groupby_list(reviews, 'user_id')
    user_cluster_dictionary = {}

    for user in user_list:
        weights = extractor.get_criteria_weights(reviews, user)
        significant_criteria, cluster_name =\
            extractor.get_significant_criteria(weights, significant_criteria_ranges)

        if cluster_name in user_cluster_dictionary:
            user_cluster_dictionary[cluster_name].append(user)
        else:
            user_cluster_dictionary[cluster_name] = [user]

    return user_cluster_dictionary


def calculate_users_similarity(user_dictionary, user_id1, user_id2, similarity_metric='euclidean'):
    """
    Calculates the similarity between two users based on how similar are their
    ratings in the reviews

    :param user_id1: the ID of user 1
    :param user_id2: the ID of user 2
    :return: a float with the similarity between the two users. Since this
    function is based on euclidean distance to calculate the similarity, a
    similarity of 0 indicates that the users share exactly the same tastes
    """
    user_weights1 = user_dictionary[user_id1].criteria_weights
    user_weights2 = user_dictionary[user_id2].criteria_weights

    return calculate_similarity(user_weights1, user_weights2, similarity_metric)


def calculate_similarity(vector1, vector2, similarity_metric='euclidean'):

    if similarity_metric == 'euclidean':
        return similarity.euclidean(vector1, vector2)
    if similarity_metric == 'cosine':
        return similarity.cosine(vector1, vector2)
    if similarity_metric == 'pearson':
        similarity_value = numpy.corrcoef(vector1, vector2)[0, 1]
        if similarity_value <= 0 or math.isnan(similarity_value):
            return None
        return similarity_value

    msg = 'Unrecognized similarity metric \'' + similarity_metric + '\''
    raise ValueError(msg)


def build_user_similarities_matrix(user_ids, user_dictionary, similarity_metric='euclidean'):
    """
    Builds a matrix that contains the similarity between every pair of users
    in the dataset of this recommender system. This is particularly useful
    to prevent repeating the same calculations in each cycle

    """
    user_similarity_matrix = {}

    for user1 in user_ids:
        user_similarity_matrix[user1] = {}
        for user2 in user_ids:
            user_similarity_matrix[user1][user2] =\
                calculate_users_similarity(user_dictionary, user1, user2, similarity_metric)

    return user_similarity_matrix