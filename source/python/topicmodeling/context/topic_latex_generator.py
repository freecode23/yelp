
import colorsys
import time

import nltk
import re
from pylatex.base_classes import CommandBase, Arguments
from pylatex import Document, Section, Subsection, Command, UnsafeCommand, Tabular, LongTabu, Itemize, NoEscape
from pylatex.package import Package

import pattern
from etl import ETLUtils
from nlp import nlp_utils
from topicmodeling.context import topic_model_creator
from topicmodeling.context.topic_model_analyzer import \
    split_topic

from utils import utilities
from utils.utilities import context_words
from utils.constants import Constants
import sys
reload(sys)
sys.setdefaultencoding('utf8')


class ColorBoxCommand(CommandBase):
    """
    A class representing a custom LaTeX command.

    This class represents a custom LaTeX command named
    ``exampleCommand``.
    """

    _latex_name = 'exampleCommand'
    packages = [Package('color')]


def extract_words(text):
    """
    Tags the words contained in the given text using part-of-speech tags

    :param text: the text to tag
    :return: a list with pairs, in the form of (word, tag)
    """
    # Remove double whitespaces
    paragraph = re.sub("\s\s+", " ", text)

    # Split the paragraph in sentences
    sentence_tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
    sentences = sentence_tokenizer.tokenize(paragraph)

    review_words = []

    for sentence in sentences:
        words = [word.lower() for word in nltk.word_tokenize(sentence)]
        review_words.extend(words)

    return review_words


def extract_topic_words(topic_model, topic_ids):

    num_terms = Constants.TOPIC_MODEL_STABILITY_NUM_TERMS

    topic_words_map = {}
    for topic_id in topic_ids:
        probability_words =\
            topic_model.print_topic(topic_id, num_terms).split(' + ')
        words = set([word.split('*')[1] for word in probability_words])
        topic_words_map[topic_id] = words

    return topic_words_map


def bold_mapper(text):
    return '\\textbf{%s}' % text


def background_color_mapper(text_color):
    text_color_split = text_color.split('|||')
    text = text_color_split[0]
    red = float(text_color_split[1])
    green = float(text_color_split[2])
    blue = float(text_color_split[3])
    return '\\colorbox[rgb]{%f,%f,%f}{%s}' % (red, green, blue, text)


class TopicLatexGenerator:

    def __init__(self, lda_based_context):
        self.lda_based_context = lda_based_context
        self.doc =\
            Document(Constants.ITEM_TYPE + '-topic-models-nouns-complete-3')
        self.num_cols = Constants.TOPIC_MODEL_STABILITY_NUM_TERMS
        self.num_topics = Constants.TOPIC_MODEL_NUM_TOPICS
        self.rgb_tuples = None
        self.automatic_context_topic_colors = None
        self.keyword_context_topic_colors = None
        self.manual_context_topic_colors = None
        self.automatic_context_topic_ids = None
        self.keyword_context_topic_ids = None
        self.manual_context_topic_ids = None
        self.automatic_context_topic_words = None
        self.keyword_context_topic_words = None
        self.manual_context_topic_words = None
        self.headers = None
        self.topic_words_map = None
        self.table_format = '|c|' + 'c|' * (self.num_cols + 1)
        self.tagger = nltk.PerceptronTagger()
        self.tag_count_map = {'NN': 0, 'JJ': 0, 'VB': 0}

        self.init_colors()
        self.init_headers()
        self.init_topic_words()
        self.init_topic_ids()
        self.doc.packages.append(Package('color'))
        new_comm = UnsafeCommand(
            'newcommand', '\exampleCommand', options=4,
            extra_arguments=r'\colorbox[rgb]{#1,#2,#3}{#4} \color{black}')
        self.doc.append(new_comm)
        new_comm2 = UnsafeCommand('tiny')
        self.doc.append(new_comm2)

    def init_colors(self):
        golden_ratio = 0.618033988749895
        hsv_tuples = [((x * golden_ratio) % 1.0, 0.5, 0.95)
                      for x in range(self.num_topics)]
        self.rgb_tuples = map(lambda hsv: colorsys.hsv_to_rgb(*hsv), hsv_tuples)

        color_index = 0
        self.automatic_context_topic_colors = {}
        for topic in self.lda_based_context.context_rich_topics:
            topic_id = topic[0]
            self.automatic_context_topic_colors[topic_id] = color_index
            # self.rgb_tuples[color_index]
            color_index += 1
        #
        # color_index = 0
        # self.keyword_context_topic_colors = {}
        # for topic_id in range(self.num_topics):
        #     topic_score = split_topic(
        #         self.lda_based_context.topic_model.print_topic(
        #             topic_id, topn=self.num_cols))
        #     if topic_score['score'] > 0:
        #         self.keyword_context_topic_colors[topic_id] = color_index
        #         color_index += 1

        color_index = 0
        self.manual_context_topic_colors = {}
        for topic in context_words[Constants.ITEM_TYPE]:
            self.manual_context_topic_colors[topic] = color_index
            color_index += 1

    def init_headers(self):
        self.headers = ['ID', 'Ratio']
        for column_index in range(self.num_cols):
            self.headers.append('Word ' + str(column_index + 1))

    def init_topic_words(self):
        # pass
        self.topic_words_map = \
            extract_topic_words(
                self.lda_based_context, range(self.num_topics))

    def init_topic_ids(self):
        self.automatic_context_topic_ids = [
            topic[0] for topic in self.lda_based_context.context_rich_topics]
        #
        # self.keyword_context_topic_ids = []
        # for topic_id in range(self.num_topics):
        #     topic_score = split_topic(
        #         self.lda_based_context.topic_model.print_topic(
        #             topic_id, topn=self.num_cols))
        #     if topic_score['score'] > 0:
        #         self.keyword_context_topic_ids.append(topic_id)

        self.manual_context_topic_ids = range(len(context_words[Constants.ITEM_TYPE]))

    def create_automatic_context_topics(self):

        with self.doc.create(Section(
                Constants.ITEM_TYPE.title() +
                ' context-rich topic models (automatic)')):
            num_context_topics = len(self.lda_based_context.context_rich_topics)

            with self.doc.create(LongTabu(self.table_format)) as table:
                table.add_hline()
                table.add_row(self.headers, mapper=bold_mapper)
                table.add_hline()

                for topic in self.lda_based_context.context_rich_topics:
                    topic_id = topic[0]
                    ratio = topic[1]
                    color_id = self.automatic_context_topic_colors[topic_id]
                    color = self.rgb_tuples[color_id]
                    id_cell = str(topic_id) + str('|||') + str(color[0]) + \
                        '|||' + str(color[1]) + '|||' + str(color[2])
                    ratio_cell = str(ratio) + str('|||') + str(color[0]) + \
                        '|||' + str(color[1]) + '|||' + str(color[2])
                    row = [id_cell, ratio_cell]
                    # row = [str(topic_id + 1)]
                    topic_words =\
                        self.lda_based_context.print_topic(
                            topic_id, self.num_cols).split(' + ')
                    for word in topic_words:
                        word_color = word + str('|||') + str(color[0]) +\
                                     '|||' + str(color[1]) + '|||' +\
                                     str(color[2])
                        row.append(word_color)
                    # row.extend(topic_words)
                    table.add_row(row, mapper=background_color_mapper)

                table.add_hline()

            self.doc.append(UnsafeCommand('par'))
            self.doc.append(
                'Number of context-rich topics: %d' % num_context_topics)

    def create_keyword_context_topics(self):
        with self.doc.create(Section(
                Constants.ITEM_TYPE.title() +
                ' context-rich topic models (keyword)')):

            num_context_topics = 0

            with self.doc.create(Tabular(self.table_format)) as table:
                table.add_hline()
                table.add_row(self.headers, mapper=bold_mapper)
                table.add_hline()

                for topic_id in range(self.num_topics):
                    topic_score = split_topic(
                        self.lda_based_context.topic_model.print_topic(
                            topic_id, topn=self.num_cols))
                    if topic_score['score'] > 0:
                        color_id = self.keyword_context_topic_colors[topic_id]
                        color = self.rgb_tuples[color_id]
                        id_cell = str(topic_id)+str('|||')+str(color[0]) + \
                            '|||'+str(color[1])+'|||'+str(color[2])
                        row = [id_cell]
                        for column_index in range(self.num_cols):
                            word = topic_score['word' + str(column_index)]
                            word_color = word+str('|||')+str(color[0])+'|||' + \
                                str(color[1])+'|||'+str(color[2])
                            row.append(word_color)
                        table.add_row(row, mapper=background_color_mapper)

                        num_context_topics += 1

                table.add_hline()

            self.doc.append(UnsafeCommand('par'))
            self.doc.append(
                'Number of context-rich topics: %d' % num_context_topics)

    def create_manual_context_topics(self):
        with self.doc.create(Section(
                Constants.ITEM_TYPE.title() +
                ' context-rich topic models (manual)')):

            with self.doc.create(Tabular(self.table_format)) as table:
                table.add_hline()
                table.add_row(self.headers, mapper=bold_mapper)
                table.add_hline()

                for topic in context_words[Constants.ITEM_TYPE]:
                    color_id = self.manual_context_topic_colors[topic]
                    color = self.rgb_tuples[color_id]
                    id_cell = str(topic)+str('|||')+str(color[0]) + \
                        '|||'+str(color[1])+'|||'+str(color[2])
                    row = [id_cell]
                    for word in list(context_words[Constants.ITEM_TYPE][topic])[:self.num_cols + 1]:
                        word_color = word+str('|||')+str(color[0])+'|||' + \
                            str(color[1])+'|||'+str(color[2])
                        row.append(word_color)
                    table.add_row(row, mapper=background_color_mapper)

                table.add_hline()

            self.doc.append(UnsafeCommand('par'))
            # self.doc.append(
            #     'Number of context-rich topics: %d' %
            #     len(context_words[Constants.ITEM_TYPE]))
            self.doc.append(ColorBoxCommand(
                arguments=Arguments(
                    1, 1, 1, 'Number of context-rich topics: ' +
                            str(len(context_words[Constants.ITEM_TYPE])))))

    def create_reviews(self):
        with self.doc.create(Section('Reviews')):
            with self.doc.create(Subsection('A subsection')):

                sg_map = {'yes': 'specific', 'no': 'generic'}

                review_index = 0
                # full_records = ETLUtils.load_json_file(
                #     Constants.FULL_PROCESSED_RECORDS_FILE)
                records_file = Constants.DATASET_FOLDER +\
                    'classified_' + Constants.ITEM_TYPE + '_reviews.json'
                full_records = ETLUtils.load_json_file(records_file)

                for record in full_records:
                    with self.doc.create(Subsection(
                                    'Review %d (%s)' % (
                            (review_index + 1), sg_map[record['specific']]))):
                        # self.build_text(record[Constants.TEXT_FIELD])
                        # for doc_part in self.build_text(
                        #         record[Constants.TEXT_FIELD]):
                        for doc_part in self.build_text_automatic(record):
                            self.doc.append(doc_part)
                    review_index += 1

    def generate_pdf(self):
        self.create_automatic_context_topics()
        # self.create_keyword_context_topics()
        # self.create_manual_context_topics()
        self.create_reviews()
        self.doc.generate_pdf()
        self.doc.generate_tex()

    def build_text(self, review):
        words = extract_words(review)
        doc_parts = []
        new_words = []
        for word in words:
            word_found = False
            for topic_id in self.automatic_context_topic_ids:
                if word in self.topic_words_map[topic_id]:
                    self.tag_word(word)
                    doc_parts.append(' '.join(new_words))
                    # doc_parts.append('topic: %d word: %s' % (topic_id, word))
                    color_id = self.automatic_context_topic_colors[topic_id]
                    color = self.rgb_tuples[color_id]
                    # doc_parts.append(ColorBoxCommand(
                    #     arguments=Arguments(
                    #         color[0], color[1], color[2], word)))
                    new_words.append(
                        '\\colorbox[rgb]{' +
                        str(color[0]) + ',' + str(color[1]) + ',' +
                        str(color[2]) + '}{' + word + '}')
                    # new_words = []
                    word_found = True
                    break
            if not word_found:
                new_words.append(word)

        print('new_words', new_words)

        self.doc.append(NoEscape(' '.join(new_words)))

        # return doc_parts

    def build_text_automatic(self, record):
        text = record[Constants.TEXT_FIELD]
        sentences = nlp_utils.get_sentences(text)
        lemmatized_words = []
        for sentence in sentences:
            lemmatized_words.append(nlp_utils.lemmatize_sentence(
                sentence, nltk.re.compile(''),
                min_length=1, max_length=100))

        doc_parts = []
        itemize = Itemize()

        for sentence in lemmatized_words:
            new_words = []
            itemize.add_item('')
            for tagged_word in sentence:
                tag = tagged_word[1]
                word = tagged_word[0]
                singular = pattern.text.en.singularize(word)
                word_found = False

                # if tag == 'VBD':
                #     new_words.append(
                #         '\\colorbox[rgb]{0.5,0.5,0.5}{' + word + '}')
                #     word_found = True
                #
                # if tag.startswith('PRP'):
                #     new_words.append(
                #         '\\colorbox[rgb]{0.85,0.85,0.85}{' + word + '}')
                #     word_found = True

                for topic_id in self.automatic_context_topic_ids:
                    if word in self.topic_words_map[topic_id]:
                    # if singular in context_words[Constants.ITEM_TYPE][topic]:
                        self.tag_word(word)
                        color_id = self.automatic_context_topic_colors[topic_id]
                        color = self.rgb_tuples[color_id]
                        new_words.append(
                            '\\colorbox[rgb]{' +
                            str(color[0]) + ',' + str(color[1]) + ',' +
                            str(color[2]) + '}{' + word + '}')
                        word_found = True
                        break
                if not word_found:
                    new_words.append(word)
            itemize.append(NoEscape(' '.join(new_words)))
        doc_parts.append(itemize)

        return doc_parts

    def build_text_manual(self, record):
        text = record[Constants.TEXT_FIELD]
        sentences = nlp_utils.get_sentences(text)
        lemmatized_words = []
        for sentence in sentences:
            lemmatized_words.append(nlp_utils.lemmatize_sentence(
                sentence, nltk.re.compile(''),
                min_length=1, max_length=100))

        doc_parts = []
        itemize = Itemize()

        for sentence in lemmatized_words:
            new_words = []
            itemize.add_item('')
            for tagged_word in sentence:
                tag = tagged_word[1]
                word = tagged_word[0]
                singular = pattern.text.en.singularize(word)
                word_found = False

                if tag == 'VBD':
                    new_words.append('\\colorbox[rgb]{0.5,0.5,0.5}{'+ word + '}')
                    word_found = True

                if tag.startswith('PRP'):
                    new_words.append('\\colorbox[rgb]{0.85,0.85,0.85}{' + word + '}')
                    word_found = True

                for topic in context_words[Constants.ITEM_TYPE]:
                    if singular in context_words[Constants.ITEM_TYPE][topic]:
                        color_id = self.manual_context_topic_colors[topic]
                        color = self.rgb_tuples[color_id]
                        new_words.append(
                            '\\colorbox[rgb]{' +
                            str(color[0]) + ',' + str(color[1]) + ',' +
                            str(color[2]) + '}{' + word + '}')
                        word_found = True
                        break
                if not word_found:
                    new_words.append(word)
            itemize.append(NoEscape(' '.join(new_words)))
        doc_parts.append(itemize)

        return doc_parts

    def tag_word(self, word):

        tagged_word = self.tagger.tag([word])[0]
        word_tag = tagged_word[1]

        if word_tag.startswith('NN'):
            self.tag_count_map['NN'] += 1
        elif word_tag.startswith('JJ'):
            self.tag_count_map['JJ'] += 1
        elif word_tag.startswith('VB'):
            self.tag_count_map['VB'] += 1
        else:
            if word_tag not in self.tag_count_map:
                self.tag_count_map[word_tag] = 0
            self.tag_count_map[word_tag] += 1

    def get_topic_statistics(self, topic_ids):

        tags_dict = {'NN': 0, 'JJ': 0, 'VB': 0}

        topic_words = set()
        for topic_id in topic_ids:
            topic_words.update(self.topic_words_map[topic_id])

        print(topic_words)
        for word in topic_words:
            tagged_word = self.tagger.tag([word])[0]
            word_tag = tagged_word[1]

            if word_tag.startswith('NN'):
                tags_dict['NN'] += 1
            elif word_tag.startswith('JJ'):
                tags_dict['JJ'] += 1
            elif word_tag.startswith('VB'):
                tags_dict['VB'] += 1
            else:
                if word_tag not in tags_dict:
                    tags_dict[word_tag] = 0
                tags_dict[word_tag] += 1

        print(tags_dict)

        total_count = 0.0
        for tag_count in tags_dict.values():
            total_count += tag_count

        print('nouns percentage: %f%%' % (tags_dict['NN'] / total_count * 100))

        return tags_dict


def main():
    utilities.plant_seeds()

    records = ETLUtils.load_json_file(Constants.PROCESSED_RECORDS_FILE)

    if Constants.SEPARATE_TOPIC_MODEL_RECSYS_REVIEWS:
        num_records = len(records)
        records = records[:num_records / 2]
    print('num_reviews', len(records))

    context_extractor = \
        topic_model_creator.create_topic_model(records, None, None)

    topic_latex_generator = TopicLatexGenerator(context_extractor)
    topic_latex_generator.generate_pdf()

start = time.time()
main()
end = time.time()
total_time = end - start
print("Total time = %f seconds" % total_time)
