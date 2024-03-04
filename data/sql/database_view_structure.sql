USE hypotermqa;

--
-- Structure for view `terms_combined`
--

DROP VIEW IF EXISTS terms_combined;
Create VIEW terms_combined as
select  
N.id as fake_term_id, N.term as fake_term, 
R.id as real_term_id, R.term as real_term, 
S.name as source,
N.explanation as fake_term_explanation, N.topic_id, 
T.name as topic, T.explanation as topic_explanation,
R.explanation as real_term_explanation, R.source_id

from nonexistent as N, 
topic as T,
nonexistent_real
 as NR,
real_terms as R,
term_source as S

where N.topic_id = T.id
and NR.nonexistent_id = N.id
and NR.real_id = R.id
and R.source_id = S.id

order by fake_term_id, real_term_id;

--
-- Structure for view `term_triplets_combined`
--

DROP VIEW IF EXISTS term_triplets_combined;
Create VIEW term_triplets_combined as
select  
TT.id as term_triplet_id,
N.id as nonexistent_id, N.term as nonexistent_term, 
R1.id as secondary_id, R1.term as secondary_term, 
R2.id as replacement_id, R2.term as replacement_term, 

R1.source_id as secondary_source_id, S1.name as secondary_source,
R1.explanation as secondary_explanation, 

R2.source_id as replacement_source_id, S2.name as replacement_source,
R2.explanation as replacement_explanation, 

N.explanation as nonexistent_explanation, N.topic_id, 
T.name as topic, T.explanation as topic_explanation

from nonexistent as N, 
term_triplets as TT,
real_terms as R1,
real_terms as R2,
term_source as S1,
term_source as S2,
topic as T

where N.topic_id = T.id
and TT.nonexistent_id = N.id
and TT.secondary_id = R1.id
and TT.replacement_id = R2.id
and R1.source_id = S1.id
and R2.source_id = S2.id

order by nonexistent_id, secondary_id;

--
-- Structure for view `combined_terms_questions`
--

DROP VIEW IF EXISTS combined_terms_questions;
Create VIEW combined_terms_questions as

select 
tq.id as question_id,
n.term as nonexistent,
R1.term as secondary,
R2.term as replacement,
tq.replacement_type,
tq.question,
tt.nonexistent_id,
tt.secondary_id,
tt.secondary_source,
tt.replacement_id,
tt.replacement_source,
tq.triplet_id

from 
terms_questions as tq,
term_triplets as tt,
nonexistent as n,
real_terms as R1,
real_terms as R2

where
tq.triplet_id = tt.id and
n.id = tt.nonexistent_id and
R1.id = tt.secondary_id and
R2.id = tt.replacement_id

order by nonexistent_id, secondary_id, replacement_type;


--
-- Structure for view `combined_terms_answers`
--

DROP VIEW IF EXISTS combined_terms_answers;
Create VIEW combined_terms_answers as

SELECT 

ta.id as answer_id,
ta.answer,
ta.question_id,
 case 
 when tq.replacement_type = 0 then True 
 else False
end as isHallucinative,
tq.replacement_type,
tq.question,
tq.nonexistent,
tq.secondary,
tq.replacement,

st.explanation as secondary_meaning,
rt.explanation as replacement_meaning,

ta.model_id as answer_source_id,
m.name as answer_source,

tq.nonexistent_id,
tq.secondary_id,
tq.secondary_source,
tq.replacement_id,
tq.replacement_source

FROM 

terms_answers as ta,
combined_terms_questions as tq,
models as m,
real_terms as st,
real_terms as rt

where ta.question_id = tq.question_id 
and ta.model_id = m.id
and st.id =tq.secondary_id
and rt.id = replacement_id

order by question_id, model_id


