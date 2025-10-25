// Normalized skill names & synonyms
module.exports = {
  synonyms: {
    react: 'React', 'react-dom': 'React', next: 'React',
    electron: 'Electron',
    typescript: 'TypeScript', ts: 'TypeScript',
    javascript: 'JavaScript', js: 'JavaScript',
    python: 'Python', py: 'Python',
    'c#': 'C#', csharp: 'C#',
    sql: 'SQL/Databases', sqlite: 'SQL/Databases', prisma: 'SQL/Databases',
    sequelize: 'SQL/Databases', mongoose: 'SQL/Databases',
    jest: 'Testing', vitest: 'Testing', mocha: 'Testing',
    docker: 'Docker', dockerfile: 'Docker', 'docker-compose': 'Docker',
    unity: 'Unity', 'unity editor': 'Unity',
    node: 'Node.js', 'node.js': 'Node.js',
    tailwind: 'Frontend Styling', sass: 'Frontend Styling', css: 'Frontend Styling',
    githubactions: 'CI/CD', 'github actions': 'CI/CD',
  },
  extToSkill: {
     '.js': 'JavaScript', '.jsx': 'JavaScript',
  '.ts': 'TypeScript',  '.tsx': 'TypeScript',
  '.sql': 'SQL/Databases',
  '.cs':  'C#',
  // everything else is ignored:
  '.md': null, '.markdown': null, '.txt': null,
  '.json': null, '.yml': null, '.yaml': null,
  '.html': null, '.htm': null, '.css': null,
  '.lock': null, '.log': null,
  '.png': null, '.jpg': null, '.jpeg': null, '.gif': null, '.svg': null, '.ico': null,
  '__noext__': null
  },
  CONF: { manifest: 1.0, config: 0.8, file: 0.6, mention: 0.3 }
};
