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

order by question_id, model_id;


--
-- Structure for view `label_answer_level`
--

DROP VIEW IF EXISTS label_answer_level;
Create VIEW label_answer_level as

SELECT 
l.id,
a.question_id,
q.question,

 case 
 when q.replacement_type = 0 then True 
 else False
end as isHypotheticalQuestion,

l.answer_id,
a.answer,
a.model_id as answer_source_id,
m1.name as answer_source,
l.evaluator_model_id,
m2.name as evaluator_model,
l.answer_label as answer_label_id,
n.name as answer_label


FROM terms_eval_answer_labels as l,
terms_answers as a
, terms_questions as q
, models as m1
, models as m2
, eval_names as n

where l.answer_id = a.id
and a.question_id = q.id
and a.model_id = m1.id
and l.evaluator_model_id = m2.id
and l.answer_label = n.id;


--
-- Structure for view `label_term_level`
--

DROP VIEW IF EXISTS label_term_level; Create VIEW label_term_level as

SELECT 
e.id as eval_id,
a.question_id,
q.question,
case 
when q.replacement_type = 0 then True 
else False
end as isHypotheticalQuestion,

e.answer_id,
a.answer,

e.term_id,
CASE 
    WHEN e.term_source = 0 THEN nt.term
    ELSE rt.term
END as term,

CASE 
    WHEN e.term_source = 0 THEN nt.explanation
    ELSE rt.explanation
END as term_explanation,

CASE 
    WHEN e.term_source = 0 THEN 1
    ELSE 0
END as IsHypotheticalTerm,


e.eval_type_id,
es.name as eval_type,
e.reflection,

e.eval_label as term_label_id,
n1.name as term_label,

l.answer_label as answer_label_id,
n2.name as answer_label,

e.term_source as term_source_id,
s.name as term_source,

a.model_id as answer_source_id,
m1.name as answer_source,
e.model_id as evaluator_model_id,
m2.name as evaluator_model

FROM terms_answers_eval as e
JOIN terms_answers as a ON e.answer_id = a.id
JOIN terms_questions as q ON a.question_id = q.id
JOIN models as m1 ON a.model_id = m1.id
JOIN models as m2 ON e.model_id = m2.id

JOIN eval_source as es ON e.eval_type_id = es.id
JOIN term_source as s ON e.term_source = s.id
JOIN terms_eval_answer_labels as l ON l.answer_id = a.id
JOIN eval_names as n1 ON e.eval_label = n1.id
JOIN eval_names as n2 ON l.answer_label = n2.id
LEFT JOIN real_terms as rt ON e.term_id = rt.id
LEFT JOIN nonexistent as nt ON e.term_id = nt.id;


--
-- Structure for view `terms_evals_detailed_explained`
--

DROP VIEW IF EXISTS terms_evals_detailed_explained; Create VIEW terms_evals_detailed_explained as

SELECT d.*, 
CASE 
    WHEN d.term_source_id = 0 THEN nt.explanation
    ELSE rt.explanation
END as explanation
FROM terms_evals_detailed as d
LEFT JOIN real_terms as rt ON d.term_id = rt.id
LEFT JOIN nonexistent as nt ON d.term_id = nt.id
order by d.eval_id;








-- ------------------------------------------------------------------------
-- VIEWS FOR LLM EVALUATION
-- ------------------------------------------------------------------------

--
-- Structure for view `terms_evals_ai_grouped`
--

DROP VIEW IF EXISTS terms_evals_ai_grouped;
Create VIEW terms_evals_ai_grouped as

SELECT answer_id, 
CASE 	
		WHEN count(distinct eval_label) = 3 THEN 1
        WHEN min(eval_label) = 1 then 1
        ELSE max(eval_label) END AS eval_label,
question_id, isHypotheticalQuestion, question, answer, answer_source_id, answer_source, evaluator_model_id, evaluator_model, count(*) as count 
FROM terms_evals_detailed
where eval_type <> 'HumanEval' and eval_type <> 'code_check'
group by question_id, answer_id, evaluator_model_id, isHypotheticalQuestion, question, answer, answer_source_id, answer_source, evaluator_model_id, evaluator_model
order by evaluator_model_id, answer_id;



--
-- Structure for view `terms_evals_labelled`
--

DROP VIEW IF EXISTS terms_evals_labelled;
Create VIEW terms_evals_labelled as

SELECT rc.answer_id,
ag.eval_label as ai_label, rc.eval_label as isRelevant_label,

CASE 	WHEN ag.eval_label = 1 THEN 1
		WHEN ag.eval_label = 2 THEN 2
		ELSE rc.eval_label END AS hallucination_label,

ag.question_id, ag.isHypotheticalQuestion, ag.question, ag.answer, ag.answer_source_id, ag.answer_source, ag.evaluator_model_id, ag.evaluator_model, ag.count

FROM 
(SELECT answer_id, term_id, max(eval_label) as eval_label FROM terms_evals_detailed where eval_type_id = 4 group by  answer_id, term_id) as rc 
left join 
terms_evals_ai_grouped as ag

on ag.answer_id = rc.answer_id;


--
-- Structure for view `terms_evals_detailed_base`
--

DROP VIEW IF EXISTS terms_evals_detailed_base;
Create VIEW terms_evals_detailed_base as

SELECT e.id as eval_id,

    a.question,
    a.answer,
    e.reflection,
    
	a.question_id,
    a.IsHallucinative as isHypotheticalQuestion,
	e.eval_label,
    n.name as eval_label_name,
    e.answer_id,
    a.answer_source_id,
    a.answer_source,
    e.eval_type_id,
    s.name as eval_type,
    e.term_source as term_source_id,
    ts.name as term_source,
    e.term_id,
    e.model_id as evaluator_model_id,
    m.name as evaluator_model
    , ae.answer_label as answer_label
FROM 
terms_answers_eval as e,
combined_terms_answers as a,
eval_source as s,
term_source as ts,
models as m, 
eval_names as n
, terms_eval_answer_labels as ae

where 
a.answer_id = e.answer_id and
e.eval_type_id = s.id and
e.model_id = m.id and
e.term_source = ts.id and
e.eval_label = n.id
and a.answer_id = ae.answer_id

order by question_id;


--
-- Structure for view `terms_evals_detailed`
--

DROP VIEW IF EXISTS terms_evals_detailed;
Create VIEW terms_evals_detailed as

SELECT eb.* , n.term, 1 as IsHypotheticalTerm
FROM terms_evals_detailed_base as eb,
nonexistent as n
where eb.term_source_id = 0
and n.id = eb.term_id

UNION

SELECT eb.* , r.term, 0 as IsHypotheticalTerm
FROM terms_evals_detailed_base as eb,
real_terms as r
where eb.term_source_id > 0
and r.id = eb.term_id;
