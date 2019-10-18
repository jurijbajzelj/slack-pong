# slack-pong
https://ngrok.com/
docker run -e POSTGRES_USER=root -e POSTGRES_DB=circle-test_test -d --rm -p 5432:5432 circleci/postgres
docker run --net=host -e "PGADMIN_DEFAULT_EMAIL=test@gmail.com" -e "PGADMIN_DEFAULT_PASSWORD=test" -v /tmp/servers.json:/pgadmin4/servers.json -d dpage/pgadmin4
