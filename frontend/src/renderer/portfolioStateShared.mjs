function getFeaturedProjectsBySavedOrder(projects = [], featuredProjectIds = []) {
  const projectMap = new Map(
    projects.map((project) => [String(project.project_id), project])
  );

  return featuredProjectIds
    .map((projectId) => projectMap.get(String(projectId)))
    .filter(Boolean)
    .slice(0, 3);
}

export {
  getFeaturedProjectsBySavedOrder,
};
