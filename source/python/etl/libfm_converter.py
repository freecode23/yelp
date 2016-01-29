
import csv

__author__ = 'fpena'


def csv_to_libfm(
        input_files, target_column, one_hot_columns,
        delete_columns=None, delimiter=',', has_header=False, suffix='.libfm'):
    """
    Converts a CSV file to the libFM format.

    :type input_files: list[str]
    :param input_files: a list with the path of the CSV files to convert
    :type target_column: int
    :param target_column: the index of the column that contains the target.
    In the case of a recommender system, the target is the rating.
    :type delete_columns: list[int]
    :param delete_columns: A list with the columns of the CSV file that are to
    be excluded
    :type delimiter: str
    :param delimiter: the separator used in the CSV file
    :type has_header: bool
    :param has_header: a boolean indicating if the CSV file has a header or not
    """

    if delete_columns is None:
        delete_columns = []

    csv_reader_list = [
        csv.reader(open(input_file, 'r'), delimiter=delimiter)
        for input_file in input_files
        ]

    data_matrix_list = []

    for csv_reader in csv_reader_list:
        if has_header:
            next(csv_reader)
        data_matrix_list.append(list(csv_reader))

    # The static columns are that ones that are not going to be deleted, don't
    # belong to the one-hot columns or the target column
    all_columns = range(len(data_matrix_list[0][0]))
    static_columns = set(all_columns).difference(
        [target_column], one_hot_columns, delete_columns)

    id_counter = 0
    output_row_list = []

    # Do the target column
    for data_matrix in data_matrix_list:
        output_rows = []
        for row_index in range(len(data_matrix)):
            output_rows.append(str(data_matrix[row_index][target_column]))
        output_row_list.append(output_rows)

    # Do the static columns
    for column_index in static_columns:

        for data_matrix, output_rows in zip(data_matrix_list, output_row_list):
            column = get_column(data_matrix, column_index)

            for row_index in range(len(data_matrix)):
                output_rows[row_index] +=\
                    " " + str(id_counter) + ":" + str(column[row_index])

        id_counter += 1

    vector_map = {}

    # Do the one-hot columns
    for data_matrix, output_rows in zip(data_matrix_list, output_row_list):
        for column_index in one_hot_columns:
            column = get_column(data_matrix, column_index)

            for row_index in range(len(data_matrix)):
                vector_key = str(column_index) + " : " + str(column[row_index])

                if vector_key not in vector_map:
                    vector_map[vector_key] = id_counter
                    id_counter += 1

                output_rows[row_index] += " " + str(vector_map[vector_key]) + ":1"

    for input_file, output_rows in zip(input_files, output_row_list):
        with open(input_file + suffix, 'w') as write_file:
            for row in output_rows:
                write_file.write("%s\n" % row)


def get_column(matrix, i):
    return [row[i] for row in matrix]
