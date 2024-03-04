USE hypotermqa;

truncate table term_source;
INSERT INTO term_source (id, name) VALUES (0, 'hypothetical');
INSERT INTO term_source (id, name) VALUES (1, 'gpt_suggestion');
INSERT INTO term_source (id, name) VALUES (2, 'title_similarity');
INSERT INTO term_source (id, name) VALUES (3, 'text_similarity');

truncate table replacement_type;
INSERT INTO replacement_type (id, name) VALUES (0, 'none');
INSERT INTO replacement_type (id, name) VALUES (1, 'programmatic');
INSERT INTO replacement_type (id, name) VALUES (2, 'gold_answer');
INSERT INTO replacement_type (id, name) VALUES (3, 'fresh');

truncate table models;
INSERT INTO models (id, name) VALUES (0, 'Human'), (1, 'gpt-3.5-turbo'), (2, 'llama2:7b-chat-q4_1'), (3, 'ChatGPT_August_3_2023'), (4, 'orca-mini:3b-q4_1'), (5, 'orca-mini:7b-q4_1'), (6, 'llama2:13b-chat-q4_K_M'), (7, 'llama2:70b-chat-q4_K_M'), (8, 'llama2:70b-chat-q4_1'), (9, 'llama2:13b-chat-q4_1'), (10, 'function');
