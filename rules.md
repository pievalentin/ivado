A new world organization has just been created. It includes all the museum management committees that have more than 2,000,000 visitors annually.  This list is available via Wikipedia: 
https://en.wikipedia.org/wiki/List_of_most_visited_museums

This new organization wishes to correlate the tourist attendance at their museums with the population of the respective cities. To achieve this, a small, common and harmonized database must be built to be able to extract features. This DB must include the characteristics of museums as well as the population of the cities in which they are located. You have been chosen to build this database. In addition, you are asked to create a small linear regression ML algorithm to correlate the city population and the influx of visitors.  Your solution must balance the need for quickly assessing the data, rapid prototyping and deploying a MVP to a (potentially) public user that could later scale. You must use the Wikipedia APIs to retrieve this list of museums and their characteristics. You are free to choose the source of your choice for the population of the cities concerned.

Deliverables:

1. **Structured Python project** implementing the data acquisition, harmonization and regression pipeline described in `implementation_plan.md`. The package must expose both CLI entry points and reusable modules so the notebook and web API can import shared logic.

2. **Dockerized services**:
   - API container running a FastAPI web server that loads the persisted regression artifact and provides `/health`, `/metrics`, and `/predict` endpoints.
   - Notebook container running Jupyter and mounting the project so the notebook can execute project code.
   - Provide a `docker-compose.yml` (or equivalent) to orchestrate the API and notebook services for local development.

3. **Jupyter notebook (`notebooks/museum_regression.ipynb`)** hosted via the Docker notebook image. The notebook must call into the packaged project to build features, train or load the regression model, and visualize results.

4. **Documentation** covering:
   - How to build and run the Docker images (including FastAPI server and notebook) and how to execute the CLI commands for training/serving.
   - Design rationale aligning with the implementation plan and noting trade-offs for data acquisition, modeling, and deployment.

You will be evaluated not only on how your code works but also on the rationale for the choices you make. 