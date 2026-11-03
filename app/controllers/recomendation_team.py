from app.utils.ai import RecomendationTeam
import psycopg
from psycopg.rows import dict_row
from app.configs import settings
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import ast


class RecomendationTeamControllers:
    @staticmethod
    async def recomendation_team(current_user, competition_id):
        skill = ",".join(
            [i["skill_name"] for i in current_user["data"]["user"]["skills"]]
        )
        pertanyaan = "team mana yang sesuai dengan konteks berikut : {}".format(
            f"yang membutuhkan skill : {skill}, dengan background : {current_user['data']['user']['skill_description']}"
        )
        user_id = current_user["data"]["user"]["id"]
        hasil = await RecomendationTeam.recomendation_team(pertanyaan)
        hasil = ast.literal_eval(hasil)
        if not hasil:
            return JSONResponse(
                content={
                    "data": [],
                    "message": "recomendation team not found",
                    "errors": None,
                },
                status_code=404,
            )
        arr = []

        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                for team in hasil:
                    team_id = team["team_id"]

                    cursor.execute(
                        """
                        SELECT
                            t.id AS team_id,
                            t.name AS team_name,
                            t.visibility,
                            t.requirement AS team_requirement,
                            c.id AS competition_id,
                            c.name AS competition_name,
                            c.description AS description,
                            COALESCE(
                                jsonb_agg(
                                    jsonb_build_object(
                                        'id', st.id,
                                        'name', st.name,
                                        'team_id', st.team_id,
                                        'created_at', st.created_at,
                                        'updated_at', st.updated_at,
                                        'deleted_at', st.deleted_at
                                    )
                                ) FILTER (WHERE st.id IS NOT NULL),
                                '[]'::jsonb
                            ) AS skills_team
                        FROM team t
                        LEFT JOIN competition c
                            ON t.competition_id = c.id
                        LEFT JOIN skills_team st
                            ON st.team_id = t.id
                            AND st.deleted_at IS NULL
                        WHERE t.id = %s
                        AND c.id = %s
                        AND t.visibility = TRUE
                        AND t.deleted_at IS NULL
                        AND c.deleted_at IS NULL
                        -- 1. Cek agar user tidak menerima rekomendasi tim yang dia sudah join (query lama)
                        AND NOT EXISTS (
                            SELECT 1
                            FROM team_role tr
                            WHERE tr.team_id = t.id
                                AND tr.user_id = %s
                                AND tr.deleted_at IS NULL
                        )
                        -- 2. Cek agar user tidak menerima rekomendasi tim yang sudah dia request join (query baru)
                        AND NOT EXISTS (
                            SELECT 1
                            FROM request_join rj
                            WHERE rj.team_id = t.id
                                AND rj.user_id = %s
                                AND rj.deleted_at IS NULL
                        )
                        GROUP BY t.id, c.id;
                        """,
                        (team_id, competition_id, user_id, user_id),
                    )

                    row = cursor.fetchone()
                    if row:
                        arr.append(row)

        return JSONResponse(
            content=jsonable_encoder(
                {
                    "data": arr,
                    "message": "success get recomendation team",
                    "errors": None,
                }
            ),
            status_code=200,
        )

    @staticmethod
    async def recomendation_team_by_team_id(current_user, competition_id, team_id):
        user_id = current_user["data"]["user"]["id"]

        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        t.id AS team_id,
                        t.name AS team_name,
                        t.visibility,
                        t.requirement AS team_requirement,
                        c.id AS competition_id,
                        c.name AS competition_name,
                        c.description AS description,
                        COALESCE(
                            jsonb_agg(
                                jsonb_build_object(
                                    'id', st.id,
                                    'name', st.name,
                                    'team_id', st.team_id,
                                    'created_at', st.created_at,
                                    'updated_at', st.updated_at,
                                    'deleted_at', st.deleted_at
                                )
                            ) FILTER (WHERE st.id IS NOT NULL),
                            '[]'::jsonb
                        ) AS skills_team
                    FROM team t
                    LEFT JOIN competition c
                        ON t.competition_id = c.id
                    LEFT JOIN skills_team st
                        ON st.team_id = t.id
                        AND st.deleted_at IS NULL
                    WHERE t.id = %s
                    AND c.id = %s
                    AND t.visibility = TRUE
                    AND t.deleted_at IS NULL
                    AND c.deleted_at IS NULL
                    -- 1. Cek agar user tidak menerima rekomendasi tim yang dia sudah join
                    AND NOT EXISTS (
                        SELECT 1
                        FROM team_role tr
                        WHERE tr.team_id = t.id
                            AND tr.user_id = %s
                            AND tr.deleted_at IS NULL
                    )
                    -- 2. Cek agar user tidak menerima rekomendasi tim yang sudah dia request join
                    AND NOT EXISTS (
                        SELECT 1
                        FROM request_join rj
                        WHERE rj.team_id = t.id
                            AND rj.user_id = %s
                            AND rj.deleted_at IS NULL
                    )
                    GROUP BY t.id, c.id;
                    """,
                    (team_id, competition_id, user_id, user_id),
                )

                row = cursor.fetchone()

        if not row:
            return JSONResponse(
                content={
                    "data": None,
                    "message": "recomendation team not found",
                    "errors": None,
                },
                status_code=404,
            )

        return JSONResponse(
            content=jsonable_encoder(
                {
                    "data": row,
                    "message": "success get recomendation team",
                    "errors": None,
                }
            ),
            status_code=200,
        )
