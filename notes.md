## to Spin up this project 

# step 1 :
<!-- start docker  -->
sudo systemctl start docker

# step 2 : 
<!-- start minio s3 bucket sample  -->
sudo docker compose up -d minio

# step 3 : 
<!-- spin up the lm studio agent  -->

# step 4 :
<!-- spin up the backend  -->
uv run uvicorn app.main:app --reload

# step 5 :
<!-- spin up the forntend  -->
npm run dev

