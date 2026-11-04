import {writeFile,mkdir} from 'node:fs/promises';
import path from 'node:path';
export default async function(){
  const target=process.env.JARVIS_E2E_STOP_FILE;
  await mkdir(path.dirname(target),{recursive:true});
  await writeFile(target,'stop');
  // Let the Python supervisor close its database/process handles before Playwright kills the shell.
  await new Promise(resolve=>setTimeout(resolve,2500));
}
