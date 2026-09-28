import { copyFile, mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

const source = join('node_modules', '@fortawesome', 'fontawesome-free');
const destination = join('static', 'vendor', 'fontawesome');

await mkdir(join(destination, 'css'), { recursive: true });
await mkdir(join(destination, 'webfonts'), { recursive: true });
await copyFile(join(source, 'css', 'all.min.css'), join(destination, 'css', 'all.min.css'));
await copyFile(join(source, 'LICENSE.txt'), join(destination, 'LICENSE.txt'));

for (const file of await readdir(join(source, 'webfonts'))) {
  if (file.endsWith('.woff2') || file.endsWith('.ttf')) {
    await copyFile(join(source, 'webfonts', file), join(destination, 'webfonts', file));
  }
}

for (const family of ['inter', 'outfit']) {
  const fontSource = join('node_modules', '@fontsource-variable', family);
  const fontDestination = join('static', 'vendor', 'fonts', family);
  await mkdir(join(fontDestination, 'files'), { recursive: true });
  const css = await readFile(join(fontSource, 'wght.css'), 'utf8');
  await writeFile(join(fontDestination, 'wght.css'), css.replaceAll(
    family === 'inter' ? 'Inter Variable' : 'Outfit Variable',
    family === 'inter' ? 'Inter' : 'Outfit'
  ));
  await copyFile(join(fontSource, 'LICENSE'), join(fontDestination, 'LICENSE'));
  for (const file of await readdir(join(fontSource, 'files'))) {
    if (file.endsWith('-wght-normal.woff2')) {
      await copyFile(join(fontSource, 'files', file), join(fontDestination, 'files', file));
    }
  }
}
