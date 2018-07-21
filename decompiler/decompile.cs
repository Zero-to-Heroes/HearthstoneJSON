using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.Decompiler.Ast.Transforms;
using ICSharpCode.ILSpy;
using ICSharpCode.ILSpy.TreeNodes;
using ICSharpCode.NRefactory.CSharp;
using ICSharpCode.NRefactory.Utils;
using Mono.Cecil;
using System;
using System.Collections;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO;
using System.Linq;
using System.Resources;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Xml;
using TextView;

static class Decompiler
{
	static int Main(string[] args)
	{
		if (args.Length != 2)
		{
			Console.WriteLine("usage: decompiler [dll] [output path]");
			return 2;
		}

		var assemblies = new AssemblyList("global");
		var assembly = assemblies.OpenAssembly(args[0]);
		var root = new AssemblyTreeNode(assembly);
		root.Decompile(new CSharpLanguage(), new PlainTextOutput(), new DecompilationOptions
		{
			SaveAsProjectDirectory = args[1],
			FullDecompilation = true,
			DecompilerSettings = new DecompilerSettings
			{
				YieldReturn = true
			}
		});
		return 0;
	}
}

// The remaining code in this file is taken from the ILSpy project,
// https://github.com/icsharpcode/ILSpy, albeit heavily pared down.

namespace TextView
{
	public class DecompilerTextView
	{
		void DecompileNodes(DecompilationContext context, ITextOutput textOutput)
		{
			var nodes = context.TreeNodes;
			for (int i = 0; i < nodes.Length; i++)
			{
				if (i > 0)
					textOutput.WriteLine();

				nodes[i].Decompile(context.Language, textOutput, context.Options);
			}
		}

		public static string CleanUpName(string text)
		{
			int pos = text.IndexOf(':');
			if (pos > 0)
				text = text.Substring(0, pos);
			pos = text.IndexOf('`');
			if (pos > 0)
				text = text.Substring(0, pos);
			text = text.Trim();
			foreach (char c in Path.GetInvalidFileNameChars())
				text = text.Replace(c, '-');
			return text;
		}

		sealed class DecompilationContext
		{
			public readonly Language Language;
			public readonly ILSpyTreeNode[] TreeNodes;
			public readonly DecompilationOptions Options;

			public DecompilationContext(Language language, ILSpyTreeNode[] treeNodes, DecompilationOptions options)
			{
				this.Language = language;
				this.TreeNodes = treeNodes;
				this.Options = options;
			}
		}
	}
}

namespace ICSharpCode.ILSpy
{
	/// <summary>
	/// Options passed to the decompiler.
	/// </summary>
	public class DecompilationOptions
	{
		/// <summary>
		/// Gets whether a full decompilation (all members recursively) is desired.
		/// If this option is false, language bindings are allowed to show the only headers of the decompiled element's children.
		/// </summary>
		public bool FullDecompilation { get; set; }

		/// <summary>
		/// Gets/Sets the directory into which the project is saved.
		/// </summary>
		public string SaveAsProjectDirectory { get; set; }

		/// <summary>
		/// Gets the settings for the decompiler.
		/// </summary>
		public DecompilerSettings DecompilerSettings { get; set; }

		public DecompilationOptions()
		{
			this.DecompilerSettings = new DecompilerSettings();
		}
	}

	/// <summary>
	/// Base class for language-specific decompiler implementations.
	/// </summary>
	public abstract class Language
	{
		/// <summary>
		/// Gets the name of the language (as shown in the UI)
		/// </summary>
		public abstract string Name { get; }

		/// <summary>
		/// Gets the file extension used by source code files in this language.
		/// </summary>
		public abstract string FileExtension { get; }

		public virtual string ProjectFileExtension
		{
			get { return null; }
		}

		public virtual void DecompileMethod(MethodDefinition method, ITextOutput output, DecompilationOptions options)
		{
			WriteCommentLine(output, TypeToString(method.DeclaringType, true) + "." + method.Name);
		}

		public virtual void DecompileProperty(PropertyDefinition property, ITextOutput output, DecompilationOptions options)
		{
			WriteCommentLine(output, TypeToString(property.DeclaringType, true) + "." + property.Name);
		}

		public virtual void DecompileField(FieldDefinition field, ITextOutput output, DecompilationOptions options)
		{
			WriteCommentLine(output, TypeToString(field.DeclaringType, true) + "." + field.Name);
		}

		public virtual void DecompileEvent(EventDefinition ev, ITextOutput output, DecompilationOptions options)
		{
			WriteCommentLine(output, TypeToString(ev.DeclaringType, true) + "." + ev.Name);
		}

		public virtual void DecompileType(TypeDefinition type, ITextOutput output, DecompilationOptions options)
		{
			WriteCommentLine(output, TypeToString(type, true));
		}

		public virtual void DecompileNamespace(string nameSpace, IEnumerable<TypeDefinition> types, ITextOutput output, DecompilationOptions options)
		{
			WriteCommentLine(output, nameSpace);
		}

		public virtual void DecompileAssembly(LoadedAssembly assembly, ITextOutput output, DecompilationOptions options)
		{
			WriteCommentLine(output, assembly.FileName);
			if (assembly.AssemblyDefinition != null)
			{
				var name = assembly.AssemblyDefinition.Name;
				if (name.IsWindowsRuntime)
				{
					WriteCommentLine(output, name.Name + " [WinRT]");
				}
				else
				{
					WriteCommentLine(output, name.FullName);
				}
			}
			else
			{
				WriteCommentLine(output, assembly.ModuleDefinition.Name);
			}
		}

		public virtual void WriteCommentLine(ITextOutput output, string comment)
		{
			output.WriteLine("// " + comment);
		}

		/// <summary>
		/// Converts a type reference into a string. This method is used by the member tree node for parameter and return types.
		/// </summary>
		public virtual string TypeToString(TypeReference type, bool includeNamespace, ICustomAttributeProvider typeAttributes = null)
		{
			if (includeNamespace)
				return type.FullName;
			else
				return type.Name;
		}

		/// <summary>
		/// Converts a member signature to a string.
		/// This is used for displaying the tooltip on a member reference.
		/// </summary>
		public virtual string GetTooltip(MemberReference member)
		{
			if (member is TypeReference)
				return TypeToString((TypeReference)member, true);
			else
				return member.ToString();
		}

		public virtual string FormatPropertyName(PropertyDefinition property, bool? isIndexer = null)
		{
			if (property == null)
				throw new ArgumentNullException("property");
			return property.Name;
		}

		public virtual string FormatTypeName(TypeDefinition type)
		{
			if (type == null)
				throw new ArgumentNullException("type");
			return type.Name;
		}

		/// <summary>
		/// Used for WPF keyboard navigation.
		/// </summary>
		public override string ToString()
		{
			return Name;
		}

		public virtual bool ShowMember(MemberReference member)
		{
			return true;
		}

		/// <summary>
		/// Used by the analyzer to map compiler generated code back to the original code's location
		/// </summary>
		public virtual MemberReference GetOriginalCodeLocation(MemberReference member)
		{
			return member;
		}
	}

	/// <summary>
	/// Decompiler logic for C#.
	/// </summary>
	public class CSharpLanguage : Language
	{
		string name = "C#";
		bool showAllMembers = false;
		Predicate<IAstTransform> transformAbortCondition = null;

		public CSharpLanguage()
		{
		}

#if DEBUG
		internal static IEnumerable<CSharpLanguage> GetDebugLanguages()
		{
			DecompilerContext context = new DecompilerContext(ModuleDefinition.CreateModule("dummy", ModuleKind.Dll));
			string lastTransformName = "no transforms";
			foreach (Type _transformType in TransformationPipeline.CreatePipeline(context).Select(v => v.GetType()).Distinct())
			{
				Type transformType = _transformType; // copy for lambda
				yield return new CSharpLanguage
				{
					transformAbortCondition = v => transformType.IsInstanceOfType(v),
					name = "C# - " + lastTransformName,
					showAllMembers = true
				};
				lastTransformName = "after " + transformType.Name;
			}
			yield return new CSharpLanguage
			{
				name = "C# - " + lastTransformName,
				showAllMembers = true
			};
		}
#endif

		public override string Name
		{
			get { return name; }
		}

		public override string FileExtension
		{
			get { return ".cs"; }
		}

		public override string ProjectFileExtension
		{
			get { return ".csproj"; }
		}

		public override void DecompileMethod(MethodDefinition method, ITextOutput output, DecompilationOptions options)
		{
			WriteCommentLine(output, TypeToString(method.DeclaringType, includeNamespace: true));
			AstBuilder codeDomBuilder = CreateAstBuilder(options, currentType: method.DeclaringType, isSingleMember: true);
			if (method.IsConstructor && !method.IsStatic && !method.DeclaringType.IsValueType)
			{
				// also fields and other ctors so that the field initializers can be shown as such
				AddFieldsAndCtors(codeDomBuilder, method.DeclaringType, method.IsStatic);
				RunTransformsAndGenerateCode(codeDomBuilder, output, options, new SelectCtorTransform(method));
			}
			else
			{
				codeDomBuilder.AddMethod(method);
				RunTransformsAndGenerateCode(codeDomBuilder, output, options);
			}
		}

		class SelectCtorTransform : IAstTransform
		{
			readonly MethodDefinition ctorDef;

			public SelectCtorTransform(MethodDefinition ctorDef)
			{
				this.ctorDef = ctorDef;
			}

			public void Run(AstNode compilationUnit)
			{
				ConstructorDeclaration ctorDecl = null;
				foreach (var node in compilationUnit.Children)
				{
					ConstructorDeclaration ctor = node as ConstructorDeclaration;
					if (ctor != null)
					{
						if (ctor.Annotation<MethodDefinition>() == ctorDef)
						{
							ctorDecl = ctor;
						}
						else
						{
							// remove other ctors
							ctor.Remove();
						}
					}
					// Remove any fields without initializers
					FieldDeclaration fd = node as FieldDeclaration;
					if (fd != null && fd.Variables.All(v => v.Initializer.IsNull))
						fd.Remove();
				}
				if (ctorDecl.Initializer.ConstructorInitializerType == ConstructorInitializerType.This)
				{
					// remove all fields
					foreach (var node in compilationUnit.Children)
						if (node is FieldDeclaration)
							node.Remove();
				}
			}
		}

		public override void DecompileProperty(PropertyDefinition property, ITextOutput output, DecompilationOptions options)
		{
			WriteCommentLine(output, TypeToString(property.DeclaringType, includeNamespace: true));
			AstBuilder codeDomBuilder = CreateAstBuilder(options, currentType: property.DeclaringType, isSingleMember: true);
			codeDomBuilder.AddProperty(property);
			RunTransformsAndGenerateCode(codeDomBuilder, output, options);
		}

		public override void DecompileField(FieldDefinition field, ITextOutput output, DecompilationOptions options)
		{
			WriteCommentLine(output, TypeToString(field.DeclaringType, includeNamespace: true));
			AstBuilder codeDomBuilder = CreateAstBuilder(options, currentType: field.DeclaringType, isSingleMember: true);
			if (field.IsLiteral)
			{
				codeDomBuilder.AddField(field);
			}
			else
			{
				// also decompile ctors so that the field initializer can be shown
				AddFieldsAndCtors(codeDomBuilder, field.DeclaringType, field.IsStatic);
			}
			RunTransformsAndGenerateCode(codeDomBuilder, output, options, new SelectFieldTransform(field));
		}

		/// <summary>
		/// Removes all top-level members except for the specified fields.
		/// </summary>
		sealed class SelectFieldTransform : IAstTransform
		{
			readonly FieldDefinition field;

			public SelectFieldTransform(FieldDefinition field)
			{
				this.field = field;
			}

			public void Run(AstNode compilationUnit)
			{
				foreach (var child in compilationUnit.Children)
				{
					if (child is EntityDeclaration)
					{
						if (child.Annotation<FieldDefinition>() != field)
							child.Remove();
					}
				}
			}
		}

		void AddFieldsAndCtors(AstBuilder codeDomBuilder, TypeDefinition declaringType, bool isStatic)
		{
			foreach (var field in declaringType.Fields)
			{
				if (field.IsStatic == isStatic)
					codeDomBuilder.AddField(field);
			}
			foreach (var ctor in declaringType.Methods)
			{
				if (ctor.IsConstructor && ctor.IsStatic == isStatic)
					codeDomBuilder.AddMethod(ctor);
			}
		}

		public override void DecompileEvent(EventDefinition ev, ITextOutput output, DecompilationOptions options)
		{
			WriteCommentLine(output, TypeToString(ev.DeclaringType, includeNamespace: true));
			AstBuilder codeDomBuilder = CreateAstBuilder(options, currentType: ev.DeclaringType, isSingleMember: true);
			codeDomBuilder.AddEvent(ev);
			RunTransformsAndGenerateCode(codeDomBuilder, output, options);
		}

		public override void DecompileType(TypeDefinition type, ITextOutput output, DecompilationOptions options)
		{
			AstBuilder codeDomBuilder = CreateAstBuilder(options, currentType: type);
			codeDomBuilder.AddType(type);
			RunTransformsAndGenerateCode(codeDomBuilder, output, options);
		}

		public override void DecompileAssembly(LoadedAssembly assembly, ITextOutput output, DecompilationOptions options)
		{
			if (options.FullDecompilation && options.SaveAsProjectDirectory != null)
			{
				HashSet<string> directories = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
				var files = WriteCodeFilesInProject(assembly.ModuleDefinition, options, directories).ToList();
				files.AddRange(WriteResourceFilesInProject(assembly, options, directories));
				WriteProjectFile(new TextOutputWriter(output), files, assembly.ModuleDefinition);
			}
			else
			{
				base.DecompileAssembly(assembly, output, options);
				output.WriteLine();
				ModuleDefinition mainModule = assembly.ModuleDefinition;
				if (mainModule.Types.Count > 0)
				{
					output.Write("// Global type: ");
					output.WriteReference(mainModule.Types[0].FullName, mainModule.Types[0]);
					output.WriteLine();
				}
				if (mainModule.EntryPoint != null)
				{
					output.Write("// Entry point: ");
					output.WriteReference(mainModule.EntryPoint.DeclaringType.FullName + "." + mainModule.EntryPoint.Name, mainModule.EntryPoint);
					output.WriteLine();
				}
				output.WriteLine("// Architecture: " + GetPlatformDisplayName(mainModule));
				if ((mainModule.Attributes & ModuleAttributes.ILOnly) == 0)
				{
					output.WriteLine("// This assembly contains unmanaged code.");
				}
				string runtimeName = GetRuntimeDisplayName(mainModule);
				if (runtimeName != null)
				{
					output.WriteLine("// Runtime: " + runtimeName);
				}
				output.WriteLine();

				// don't automatically load additional assemblies when an assembly node is selected in the tree view
				// using (options.FullDecompilation ? null : LoadedAssembly.DisableAssemblyLoad())
				{
					AstBuilder codeDomBuilder = CreateAstBuilder(options, currentModule: assembly.ModuleDefinition);
					codeDomBuilder.AddAssembly(assembly.ModuleDefinition, onlyAssemblyLevel: !options.FullDecompilation);
					codeDomBuilder.RunTransformations(transformAbortCondition);
					codeDomBuilder.GenerateCode(output);
				}
			}
		}

		#region WriteProjectFile
		void WriteProjectFile(TextWriter writer, IEnumerable<Tuple<string, string>> files, ModuleDefinition module)
		{
			const string ns = "http://schemas.microsoft.com/developer/msbuild/2003";
			string platformName = GetPlatformName(module);
			Guid guid = Guid.NewGuid();
			using (XmlTextWriter w = new XmlTextWriter(writer))
			{
				w.Formatting = Formatting.Indented;
				w.WriteStartDocument();
				w.WriteStartElement("Project", ns);
				w.WriteAttributeString("ToolsVersion", "4.0");
				w.WriteAttributeString("DefaultTargets", "Build");

				w.WriteStartElement("PropertyGroup");
				w.WriteElementString("ProjectGuid", guid.ToString("B").ToUpperInvariant());

				w.WriteStartElement("Configuration");
				w.WriteAttributeString("Condition", " '$(Configuration)' == '' ");
				w.WriteValue("Debug");
				w.WriteEndElement(); // </Configuration>

				w.WriteStartElement("Platform");
				w.WriteAttributeString("Condition", " '$(Platform)' == '' ");
				w.WriteValue(platformName);
				w.WriteEndElement(); // </Platform>

				switch (module.Kind)
				{
					case ModuleKind.Windows:
						w.WriteElementString("OutputType", "WinExe");
						break;
					case ModuleKind.Console:
						w.WriteElementString("OutputType", "Exe");
						break;
					default:
						w.WriteElementString("OutputType", "Library");
						break;
				}

				w.WriteElementString("AssemblyName", module.Assembly.Name.Name);
				bool useTargetFrameworkAttribute = false;
				var targetFrameworkAttribute = module.Assembly.CustomAttributes.FirstOrDefault(a => a.AttributeType.FullName == "System.Runtime.Versioning.TargetFrameworkAttribute");
				if (targetFrameworkAttribute != null && targetFrameworkAttribute.ConstructorArguments.Any())
				{
					string frameworkName = (string)targetFrameworkAttribute.ConstructorArguments[0].Value;
					string[] frameworkParts = frameworkName.Split(',');
					string frameworkVersion = frameworkParts.FirstOrDefault(a => a.StartsWith("Version="));
					if (frameworkVersion != null)
					{
						w.WriteElementString("TargetFrameworkVersion", frameworkVersion.Substring("Version=".Length));
						useTargetFrameworkAttribute = true;
					}
					string frameworkProfile = frameworkParts.FirstOrDefault(a => a.StartsWith("Profile="));
					if (frameworkProfile != null)
						w.WriteElementString("TargetFrameworkProfile", frameworkProfile.Substring("Profile=".Length));
				}
				if (!useTargetFrameworkAttribute)
				{
					switch (module.Runtime)
					{
						case TargetRuntime.Net_1_0:
							w.WriteElementString("TargetFrameworkVersion", "v1.0");
							break;
						case TargetRuntime.Net_1_1:
							w.WriteElementString("TargetFrameworkVersion", "v1.1");
							break;
						case TargetRuntime.Net_2_0:
							w.WriteElementString("TargetFrameworkVersion", "v2.0");
							// TODO: Detect when .NET 3.0/3.5 is required
							break;
						default:
							w.WriteElementString("TargetFrameworkVersion", "v4.0");
							break;
					}
				}
				w.WriteElementString("WarningLevel", "4");

				w.WriteEndElement(); // </PropertyGroup>

				w.WriteStartElement("PropertyGroup"); // platform-specific
				w.WriteAttributeString("Condition", " '$(Platform)' == '" + platformName + "' ");
				w.WriteElementString("PlatformTarget", platformName);
				w.WriteEndElement(); // </PropertyGroup> (platform-specific)

				w.WriteStartElement("PropertyGroup"); // Debug
				w.WriteAttributeString("Condition", " '$(Configuration)' == 'Debug' ");
				w.WriteElementString("OutputPath", "bin\\Debug\\");
				w.WriteElementString("DebugSymbols", "true");
				w.WriteElementString("DebugType", "full");
				w.WriteElementString("Optimize", "false");
				w.WriteEndElement(); // </PropertyGroup> (Debug)

				w.WriteStartElement("PropertyGroup"); // Release
				w.WriteAttributeString("Condition", " '$(Configuration)' == 'Release' ");
				w.WriteElementString("OutputPath", "bin\\Release\\");
				w.WriteElementString("DebugSymbols", "true");
				w.WriteElementString("DebugType", "pdbonly");
				w.WriteElementString("Optimize", "true");
				w.WriteEndElement(); // </PropertyGroup> (Release)


				w.WriteStartElement("ItemGroup"); // References
				foreach (AssemblyNameReference r in module.AssemblyReferences)
				{
					if (r.Name != "mscorlib")
					{
						w.WriteStartElement("Reference");
						w.WriteAttributeString("Include", r.Name);
						w.WriteEndElement();
					}
				}
				w.WriteEndElement(); // </ItemGroup> (References)

				foreach (IGrouping<string, string> gr in (from f in files group f.Item2 by f.Item1 into g orderby g.Key select g))
				{
					w.WriteStartElement("ItemGroup");
					foreach (string file in gr.OrderBy(f => f, StringComparer.OrdinalIgnoreCase))
					{
						w.WriteStartElement(gr.Key);
						w.WriteAttributeString("Include", file);
						w.WriteEndElement();
					}
					w.WriteEndElement();
				}

				w.WriteStartElement("Import");
				w.WriteAttributeString("Project", "$(MSBuildToolsPath)\\Microsoft.CSharp.targets");
				w.WriteEndElement();

				w.WriteEndDocument();
			}
		}
		#endregion

		#region WriteCodeFilesInProject
		bool IncludeTypeWhenDecompilingProject(TypeDefinition type, DecompilationOptions options)
		{
			if (type.Name == "<Module>" || AstBuilder.MemberIsHidden(type, options.DecompilerSettings))
				return false;
			if (type.Namespace == "XamlGeneratedNamespace" && type.Name == "GeneratedInternalTypeHelper")
				return false;
			return true;
		}

		IEnumerable<Tuple<string, string>> WriteAssemblyInfo(ModuleDefinition module, DecompilationOptions options, HashSet<string> directories)
		{
			// don't automatically load additional assemblies when an assembly node is selected in the tree view
			// using (LoadedAssembly.DisableAssemblyLoad())
			{
				AstBuilder codeDomBuilder = CreateAstBuilder(options, currentModule: module);
				codeDomBuilder.AddAssembly(module, onlyAssemblyLevel: true);
				codeDomBuilder.RunTransformations(transformAbortCondition);

				string prop = "Properties";
				if (directories.Add("Properties"))
					Directory.CreateDirectory(Path.Combine(options.SaveAsProjectDirectory, prop));
				string assemblyInfo = Path.Combine(prop, "AssemblyInfo" + this.FileExtension);
				using (StreamWriter w = new StreamWriter(Path.Combine(options.SaveAsProjectDirectory, assemblyInfo)))
					codeDomBuilder.GenerateCode(new PlainTextOutput(w));
				return new Tuple<string, string>[] { Tuple.Create("Compile", assemblyInfo) };
			}
		}

		IEnumerable<Tuple<string, string>> WriteCodeFilesInProject(ModuleDefinition module, DecompilationOptions options, HashSet<string> directories)
		{
			var files = module.Types.Where(t => IncludeTypeWhenDecompilingProject(t, options)).GroupBy(
				delegate (TypeDefinition type) {
					string file = TextView.DecompilerTextView.CleanUpName(type.Name) + this.FileExtension;
					if (string.IsNullOrEmpty(type.Namespace))
					{
						return file;
					}
					else
					{
						string dir = TextView.DecompilerTextView.CleanUpName(type.Namespace);
						if (directories.Add(dir))
							Directory.CreateDirectory(Path.Combine(options.SaveAsProjectDirectory, dir));
						return Path.Combine(dir, file);
					}
				}, StringComparer.OrdinalIgnoreCase).ToList();
			foreach (IGrouping<string, TypeDefinition> file in files) {
				using (StreamWriter w = new StreamWriter(Path.Combine(options.SaveAsProjectDirectory, file.Key)))
				{
					AstBuilder codeDomBuilder = CreateAstBuilder(options, currentModule: module);
					foreach (TypeDefinition type in file)
					{
						codeDomBuilder.AddType(type);
					}
					codeDomBuilder.RunTransformations(transformAbortCondition);
					codeDomBuilder.GenerateCode(new PlainTextOutput(w));
				}
			}
			AstMethodBodyBuilder.PrintNumberOfUnhandledOpcodes();
			return files.Select(f => Tuple.Create("Compile", f.Key)).Concat(WriteAssemblyInfo(module, options, directories));
		}
		#endregion

		#region WriteResourceFilesInProject
		IEnumerable<Tuple<string, string>> WriteResourceFilesInProject(LoadedAssembly assembly, DecompilationOptions options, HashSet<string> directories)
		{
			//AppDomain bamlDecompilerAppDomain = null;
			//try {
			foreach (EmbeddedResource r in assembly.ModuleDefinition.Resources.OfType<EmbeddedResource>())
			{
				string fileName;
				Stream s = r.GetResourceStream();
				s.Position = 0;
				if (r.Name.EndsWith(".g.resources", StringComparison.OrdinalIgnoreCase))
				{
					IEnumerable<DictionaryEntry> rs = null;
					try
					{
						rs = new ResourceSet(s).Cast<DictionaryEntry>();
					}
					catch (ArgumentException)
					{
					}
					if (rs != null && rs.All(e => e.Value is Stream))
					{
						foreach (var pair in rs)
						{
							fileName = Path.Combine(((string)pair.Key).Split('/').Select(p => TextView.DecompilerTextView.CleanUpName(p)).ToArray());
							string dirName = Path.GetDirectoryName(fileName);
							if (!string.IsNullOrEmpty(dirName) && directories.Add(dirName))
							{
								Directory.CreateDirectory(Path.Combine(options.SaveAsProjectDirectory, dirName));
							}
							Stream entryStream = (Stream)pair.Value;
							entryStream.Position = 0;
							if (fileName.EndsWith(".baml", StringComparison.OrdinalIgnoreCase))
							{
								//									MemoryStream ms = new MemoryStream();
								//									entryStream.CopyTo(ms);
								// TODO implement extension point
								//									var decompiler = Baml.BamlResourceEntryNode.CreateBamlDecompilerInAppDomain(ref bamlDecompilerAppDomain, assembly.FileName);
								//									string xaml = null;
								//									try {
								//										xaml = decompiler.DecompileBaml(ms, assembly.FileName, new ConnectMethodDecompiler(assembly), new AssemblyResolver(assembly));
								//									}
								//									catch (XamlXmlWriterException) { } // ignore XAML writer exceptions
								//									if (xaml != null) {
								//										File.WriteAllText(Path.Combine(options.SaveAsProjectDirectory, Path.ChangeExtension(fileName, ".xaml")), xaml);
								//										yield return Tuple.Create("Page", Path.ChangeExtension(fileName, ".xaml"));
								//										continue;
								//									}
							}
							using (FileStream fs = new FileStream(Path.Combine(options.SaveAsProjectDirectory, fileName), FileMode.Create, FileAccess.Write))
							{
								entryStream.CopyTo(fs);
							}
							yield return Tuple.Create("Resource", fileName);
						}
						continue;
					}
				}
				fileName = GetFileNameForResource(r.Name, directories);
				using (FileStream fs = new FileStream(Path.Combine(options.SaveAsProjectDirectory, fileName), FileMode.Create, FileAccess.Write))
				{
					s.CopyTo(fs);
				}
				yield return Tuple.Create("EmbeddedResource", fileName);
			}
			//}
			//finally {
			//    if (bamlDecompilerAppDomain != null)
			//        AppDomain.Unload(bamlDecompilerAppDomain);
			//}
		}

		string GetFileNameForResource(string fullName, HashSet<string> directories)
		{
			string[] splitName = fullName.Split('.');
			string fileName = TextView.DecompilerTextView.CleanUpName(fullName);
			for (int i = splitName.Length - 1; i > 0; i--)
			{
				string ns = string.Join(".", splitName, 0, i);
				if (directories.Contains(ns))
				{
					string name = string.Join(".", splitName, i, splitName.Length - i);
					fileName = Path.Combine(ns, TextView.DecompilerTextView.CleanUpName(name));
					break;
				}
			}
			return fileName;
		}
		#endregion

		void RunTransformsAndGenerateCode(AstBuilder astBuilder, ITextOutput output, DecompilationOptions options, IAstTransform additionalTransform = null)
		{
			astBuilder.RunTransformations(transformAbortCondition);
			if (additionalTransform != null)
			{
				additionalTransform.Run(astBuilder.SyntaxTree);
			}
			astBuilder.GenerateCode(output);
		}

		public static string GetPlatformDisplayName(ModuleDefinition module)
		{
			switch (module.Architecture)
			{
				case TargetArchitecture.I386:
					if ((module.Attributes & ModuleAttributes.Preferred32Bit) == ModuleAttributes.Preferred32Bit)
						return "AnyCPU (32-bit preferred)";
					else if ((module.Attributes & ModuleAttributes.Required32Bit) == ModuleAttributes.Required32Bit)
						return "x86";
					else
						return "AnyCPU (64-bit preferred)";
				case TargetArchitecture.AMD64:
					return "x64";
				case TargetArchitecture.IA64:
					return "Itanium";
				default:
					return module.Architecture.ToString();
			}
		}

		public static string GetPlatformName(ModuleDefinition module)
		{
			switch (module.Architecture)
			{
				case TargetArchitecture.I386:
					if ((module.Attributes & ModuleAttributes.Preferred32Bit) == ModuleAttributes.Preferred32Bit)
						return "AnyCPU";
					else if ((module.Attributes & ModuleAttributes.Required32Bit) == ModuleAttributes.Required32Bit)
						return "x86";
					else
						return "AnyCPU";
				case TargetArchitecture.AMD64:
					return "x64";
				case TargetArchitecture.IA64:
					return "Itanium";
				default:
					return module.Architecture.ToString();
			}
		}

		public static string GetRuntimeDisplayName(ModuleDefinition module)
		{
			switch (module.Runtime)
			{
				case TargetRuntime.Net_1_0:
					return ".NET 1.0";
				case TargetRuntime.Net_1_1:
					return ".NET 1.1";
				case TargetRuntime.Net_2_0:
					return ".NET 2.0";
				case TargetRuntime.Net_4_0:
					return ".NET 4.0";
			}
			return null;
		}

		AstBuilder CreateAstBuilder(DecompilationOptions options, ModuleDefinition currentModule = null, TypeDefinition currentType = null, bool isSingleMember = false)
		{
			if (currentModule == null)
				currentModule = currentType.Module;
			DecompilerSettings settings = options.DecompilerSettings;
			if (isSingleMember)
			{
				settings = settings.Clone();
				settings.UsingDeclarations = false;
			}
			return new AstBuilder(
				new DecompilerContext(currentModule)
				{
					CancellationToken = new System.Threading.CancellationToken(),
					CurrentType = currentType,
					Settings = settings
				});
		}

		public override string TypeToString(TypeReference type, bool includeNamespace, ICustomAttributeProvider typeAttributes = null)
		{
			ConvertTypeOptions options = ConvertTypeOptions.IncludeTypeParameterDefinitions;
			if (includeNamespace)
				options |= ConvertTypeOptions.IncludeNamespace;

			return TypeToString(options, type, typeAttributes);
		}

		string TypeToString(ConvertTypeOptions options, TypeReference type, ICustomAttributeProvider typeAttributes = null)
		{
			AstType astType = AstBuilder.ConvertType(type, typeAttributes, options);

			StringWriter w = new StringWriter();
			if (type.IsByReference)
			{
				ParameterDefinition pd = typeAttributes as ParameterDefinition;
				if (pd != null && (!pd.IsIn && pd.IsOut))
					w.Write("out ");
				else
					w.Write("ref ");

				if (astType is ComposedType && ((ComposedType)astType).PointerRank > 0)
					((ComposedType)astType).PointerRank--;
			}

			astType.AcceptVisitor(new CSharpOutputVisitor(w, FormattingOptionsFactory.CreateAllman()));
			return w.ToString();
		}

		public override string FormatPropertyName(PropertyDefinition property, bool? isIndexer)
		{
			if (property == null)
				throw new ArgumentNullException("property");

			if (!isIndexer.HasValue)
			{
				isIndexer = property.IsIndexer();
			}
			if (isIndexer.Value)
			{
				var buffer = new System.Text.StringBuilder();
				var accessor = property.GetMethod ?? property.SetMethod;
				if (accessor.HasOverrides)
				{
					var declaringType = accessor.Overrides.First().DeclaringType;
					buffer.Append(TypeToString(declaringType, includeNamespace: true));
					buffer.Append(@".");
				}
				buffer.Append(@"this[");
				bool addSeparator = false;
				foreach (var p in property.Parameters)
				{
					if (addSeparator)
						buffer.Append(@", ");
					else
						addSeparator = true;
					buffer.Append(TypeToString(p.ParameterType, includeNamespace: true));
				}
				buffer.Append(@"]");
				return buffer.ToString();
			}
			else
				return property.Name;
		}

		public override string FormatTypeName(TypeDefinition type)
		{
			if (type == null)
				throw new ArgumentNullException("type");

			return TypeToString(ConvertTypeOptions.DoNotUsePrimitiveTypeNames | ConvertTypeOptions.IncludeTypeParameterDefinitions, type);
		}

		public override bool ShowMember(MemberReference member)
		{
			return showAllMembers || !AstBuilder.MemberIsHidden(member, new DecompilationOptions().DecompilerSettings);
		}

		public override string GetTooltip(MemberReference member)
		{
			MethodDefinition md = member as MethodDefinition;
			PropertyDefinition pd = member as PropertyDefinition;
			EventDefinition ed = member as EventDefinition;
			FieldDefinition fd = member as FieldDefinition;
			if (md != null || pd != null || ed != null || fd != null)
			{
				AstBuilder b = new AstBuilder(new DecompilerContext(member.Module) { Settings = new DecompilerSettings { UsingDeclarations = false } });
				b.DecompileMethodBodies = false;
				if (md != null)
					b.AddMethod(md);
				else if (pd != null)
					b.AddProperty(pd);
				else if (ed != null)
					b.AddEvent(ed);
				else
					b.AddField(fd);
				b.RunTransformations();
				foreach (var attribute in b.SyntaxTree.Descendants.OfType<AttributeSection>())
					attribute.Remove();

				StringWriter w = new StringWriter();
				b.GenerateCode(new PlainTextOutput(w));
				return Regex.Replace(w.ToString(), @"\s+", " ").TrimEnd();
			}

			return base.GetTooltip(member);
		}
	}

	/// <summary>
	/// Represents an assembly loaded into ILSpy.
	/// </summary>
	public sealed class LoadedAssembly
	{
		readonly ModuleDefinition assembly;
		readonly AssemblyList assemblyList;
		readonly string fileName;
		readonly string shortName;

		public LoadedAssembly(AssemblyList assemblyList, string fileName, Stream stream = null)
		{
			if (assemblyList == null)
				throw new ArgumentNullException("assemblyList");
			if (fileName == null)
				throw new ArgumentNullException("fileName");
			this.assemblyList = assemblyList;
			this.fileName = fileName;

			this.assembly = LoadAssembly(stream); // requires that this.fileName is set
			this.shortName = Path.GetFileNameWithoutExtension(fileName);
		}

		/// <summary>
		/// Gets the Cecil ModuleDefinition.
		/// Can be null when there was a load error.
		/// </summary>
		public ModuleDefinition ModuleDefinition
		{
			get
			{
				try
				{
					return assembly;
				}
				catch (AggregateException)
				{
					return null;
				}
			}
		}

		/// <summary>
		/// Gets the Cecil AssemblyDefinition.
		/// Is null when there was a load error; or when opening a netmodule.
		/// </summary>
		public AssemblyDefinition AssemblyDefinition
		{
			get
			{
				var module = this.ModuleDefinition;
				return module != null ? module.Assembly : null;
			}
		}

		public AssemblyList AssemblyList
		{
			get { return assemblyList; }
		}

		public string FileName
		{
			get { return fileName; }
		}

		public string ShortName
		{
			get { return shortName; }
		}

		public string Text
		{
			get
			{
				if (AssemblyDefinition != null)
				{
					return String.Format("{0} ({1})", ShortName, AssemblyDefinition.Name.Version);
				}
				else
				{
					return ShortName;
				}
			}
		}

		public bool IsLoaded
		{
			get { return assembly != null; }
		}

		public bool HasLoadError
		{
			get { return assembly == null; }
		}

		public bool IsAutoLoaded { get; set; }

		ModuleDefinition LoadAssembly(Stream stream)
		{
			ModuleDefinition module;

			// runs on background thread
			ReaderParameters p = new ReaderParameters();
			p.AssemblyResolver = new MyAssemblyResolver(this);

			if (stream != null)
			{
				// Read the module from a precrafted stream
				module = ModuleDefinition.ReadModule(stream, p);
			}
			else
			{
				// Read the module from disk (by default)
				module = ModuleDefinition.ReadModule(fileName, p);
			}
			return module;
		}

		sealed class MyAssemblyResolver : IAssemblyResolver
		{
			readonly LoadedAssembly parent;

			public MyAssemblyResolver(LoadedAssembly parent)
			{
				this.parent = parent;
			}

			public AssemblyDefinition Resolve(AssemblyNameReference name)
			{
				var node = parent.LookupReferencedAssembly(name);
				return node != null ? node.AssemblyDefinition : null;
			}

			public AssemblyDefinition Resolve(AssemblyNameReference name, ReaderParameters parameters)
			{
				var node = parent.LookupReferencedAssembly(name);
				return node != null ? node.AssemblyDefinition : null;
			}

			public AssemblyDefinition Resolve(string fullName)
			{
				var node = parent.LookupReferencedAssembly(fullName);
				return node != null ? node.AssemblyDefinition : null;
			}

			public AssemblyDefinition Resolve(string fullName, ReaderParameters parameters)
			{
				var node = parent.LookupReferencedAssembly(fullName);
				return node != null ? node.AssemblyDefinition : null;
			}
		}

		public IAssemblyResolver GetAssemblyResolver()
		{
			return new MyAssemblyResolver(this);
		}

		public LoadedAssembly LookupReferencedAssembly(AssemblyNameReference name)
		{
			if (name == null)
				throw new ArgumentNullException("name");
			if (name.IsWindowsRuntime)
			{
				return assemblyList.winRTMetadataLookupCache.GetOrAdd(name.Name, LookupWinRTMetadata);
			}
			else
			{
				return assemblyList.assemblyLookupCache.GetOrAdd(name.FullName, LookupReferencedAssemblyInternal);
			}
		}

		public LoadedAssembly LookupReferencedAssembly(string fullName)
		{
			return assemblyList.assemblyLookupCache.GetOrAdd(fullName, LookupReferencedAssemblyInternal);
		}

		LoadedAssembly LookupReferencedAssemblyInternal(string fullName)
		{
			foreach (LoadedAssembly asm in assemblyList.GetAssemblies())
			{
				if (asm.AssemblyDefinition != null && fullName.Equals(asm.AssemblyDefinition.FullName, StringComparison.OrdinalIgnoreCase))
					return asm;
			}

			var name = AssemblyNameReference.Parse(fullName);
			string file = null;
			if (file == null)
			{
				string dir = Path.GetDirectoryName(this.fileName);
				if (File.Exists(Path.Combine(dir, name.Name + ".dll")))
					file = Path.Combine(dir, name.Name + ".dll");
				else if (File.Exists(Path.Combine(dir, name.Name + ".exe")))
					file = Path.Combine(dir, name.Name + ".exe");
			}
			if (file != null)
			{
				var loaded = assemblyList.OpenAssembly(file, true);
				return loaded;
			}
			else
			{
				return null;
			}
		}

		LoadedAssembly LookupWinRTMetadata(string name)
		{
			foreach (LoadedAssembly asm in assemblyList.GetAssemblies())
			{
				if (asm.AssemblyDefinition != null && name.Equals(asm.AssemblyDefinition.Name.Name, StringComparison.OrdinalIgnoreCase))
					return asm;
			}

			string file = Path.Combine(Environment.SystemDirectory, "WinMetadata", name + ".winmd");
			if (File.Exists(file))
			{
				return assemblyList.OpenAssembly(file, true);
			}
			else
			{
				return null;
			}
		}
	}

	public sealed class AssemblyList
	{
		readonly string listName;

		/// <summary>Dirty flag, used to mark modifications so that the list is saved later</summary>
		bool dirty;

		internal readonly ConcurrentDictionary<string, LoadedAssembly> assemblyLookupCache = new ConcurrentDictionary<string, LoadedAssembly>();
		internal readonly ConcurrentDictionary<string, LoadedAssembly> winRTMetadataLookupCache = new ConcurrentDictionary<string, LoadedAssembly>();

		/// <summary>
		/// The assemblies in this list.
		/// Needs locking for multi-threaded access!
		/// Write accesses are allowed on the GUI thread only (but still need locking!)
		/// </summary>
		/// <remarks>
		/// Technically read accesses need locking when done on non-GUI threads... but whenever possible, use the
		/// thread-safe <see cref="GetAssemblies()"/> method.
		/// </remarks>
		internal readonly ObservableCollection<LoadedAssembly> assemblies = new ObservableCollection<LoadedAssembly>();

		public AssemblyList(string listName)
		{
			this.listName = listName;
		}

		/// <summary>
		/// Gets the loaded assemblies. This method is thread-safe.
		/// </summary>
		public LoadedAssembly[] GetAssemblies()
		{
			lock (assemblies)
			{
				return assemblies.ToArray();
			}
		}

		/// <summary>
		/// Gets the name of this list.
		/// </summary>
		public string ListName
		{
			get { return listName; }
		}

		/// <summary>
		/// Opens an assembly from disk.
		/// Returns the existing assembly node if it is already loaded.
		/// </summary>
		public LoadedAssembly OpenAssembly(string file, bool isAutoLoaded = false)
		{
			file = Path.GetFullPath(file);

			foreach (LoadedAssembly asm in this.assemblies)
			{
				if (file.Equals(asm.FileName, StringComparison.OrdinalIgnoreCase))
					return asm;
			}

			var newAsm = new LoadedAssembly(this, file);
			newAsm.IsAutoLoaded = isAutoLoaded;
			lock (assemblies)
			{
				this.assemblies.Add(newAsm);
			}
			return newAsm;
		}

		/// <summary>
		/// Replace the assembly object model from a crafted stream, without disk I/O
		/// Returns null if it is not already loaded.
		/// </summary>
		public LoadedAssembly HotReplaceAssembly(string file, Stream stream)
		{
			file = Path.GetFullPath(file);

			var target = this.assemblies.FirstOrDefault(asm => file.Equals(asm.FileName, StringComparison.OrdinalIgnoreCase));
			if (target == null)
				return null;

			var index = this.assemblies.IndexOf(target);
			var newAsm = new LoadedAssembly(this, file, stream);
			newAsm.IsAutoLoaded = target.IsAutoLoaded;
			lock (assemblies)
			{
				this.assemblies.Remove(target);
				this.assemblies.Insert(index, newAsm);
			}
			return newAsm;
		}

		public void Sort(IComparer<LoadedAssembly> comparer)
		{
			Sort(0, int.MaxValue, comparer);
		}

		public void Sort(int index, int count, IComparer<LoadedAssembly> comparer)
		{
			lock (assemblies)
			{
				List<LoadedAssembly> list = new List<LoadedAssembly>(assemblies);
				list.Sort(index, Math.Min(count, list.Count - index), comparer);
				assemblies.Clear();
				foreach (var it in list)
				{
					assemblies.Add(it);
				}
			}
		}
	}
}

namespace ICSharpCode.ILSpy.TreeNodes
{
	/// <summary>
	/// Base class of all ILSpy tree nodes.
	/// </summary>
	public abstract class ILSpyTreeNode
	{
		static Language csharp = new CSharpLanguage();
		public Language Language
		{
			get { return csharp; }
		}

		public List<ILSpyTreeNode> Children = new List<ILSpyTreeNode>();
		protected virtual void LoadChildren() { }

		protected static object HighlightSearchMatch(string text, string suffix = null)
		{
			// TODO: implement highlighting the search match
			return text + suffix;
		}

		public abstract void Decompile(Language language, ITextOutput output, DecompilationOptions options);

		/// <summary>
		/// Used to implement special view logic for some items.
		/// This method is called on the main thread when only a single item is selected.
		/// If it returns false, normal decompilation is used to view the item.
		/// </summary>
		public virtual bool View(TextView.DecompilerTextView textView)
		{
			return false;
		}

		/// <summary>
		/// Used to implement special save logic for some items.
		/// This method is called on the main thread when only a single item is selected.
		/// If it returns false, normal decompilation is used to save the item.
		/// </summary>
		public virtual bool Save(TextView.DecompilerTextView textView)
		{
			return false;
		}

		public virtual bool IsPublicAPI
		{
			get { return true; }
		}

		public virtual bool IsAutoLoaded
		{
			get { return false; }
		}
	}

	/// <summary>
	/// Tree node representing an assembly.
	/// This class is responsible for loading both namespace and type nodes.
	/// </summary>
	public sealed class AssemblyTreeNode : ILSpyTreeNode
	{
		readonly LoadedAssembly assembly;
		readonly Dictionary<string, NamespaceTreeNode> namespaces = new Dictionary<string, NamespaceTreeNode>();

		public AssemblyTreeNode(LoadedAssembly assembly)
		{
			if (assembly == null)
				throw new ArgumentNullException("assembly");

			this.assembly = assembly;
		}

		public LoadedAssembly LoadedAssembly
		{
			get { return assembly; }
		}

		readonly Dictionary<TypeDefinition, TypeTreeNode> typeDict = new Dictionary<TypeDefinition, TypeTreeNode>();
		protected override void LoadChildren()
		{
			ModuleDefinition moduleDefinition = assembly.ModuleDefinition;
			if (moduleDefinition == null)
			{
				// if we crashed on loading, then we don't have any children
				return;
			}

			foreach (NamespaceTreeNode ns in namespaces.Values)
			{
				ns.Children.Clear();
			}
			foreach (TypeDefinition type in moduleDefinition.Types.OrderBy(t => t.FullName))
			{
				NamespaceTreeNode ns;
				if (!namespaces.TryGetValue(type.Namespace, out ns))
				{
					ns = new NamespaceTreeNode(type.Namespace);
					namespaces[type.Namespace] = ns;
				}
				TypeTreeNode node = new TypeTreeNode(type, this);
				typeDict[type] = node;
				ns.Children.Add(node);
			}
			foreach (NamespaceTreeNode ns in namespaces.Values.OrderBy(n => n.Name))
			{
				if (ns.Children.Count > 0)
					this.Children.Add(ns);
			}
		}

		public override void Decompile(Language language, ITextOutput output, DecompilationOptions options)
		{
			language.DecompileAssembly(assembly, output, options);
		}

		public AssemblyList AssemblyList
		{
			get { return assembly.AssemblyList; }
		}
	}

	/// <summary>
	/// Namespace node. The loading of the type nodes is handled by the parent AssemblyTreeNode.
	/// </summary>
	public sealed class NamespaceTreeNode : ILSpyTreeNode
	{
		readonly string name;

		public string Name
		{
			get { return name; }
		}

		public NamespaceTreeNode(string name)
		{
			if (name == null)
				throw new ArgumentNullException("name");
			this.name = name;
		}

		public override void Decompile(Language language, ITextOutput output, DecompilationOptions options)
		{
			language.DecompileNamespace(name, this.Children.OfType<TypeTreeNode>().Select(t => t.TypeDefinition), output, options);
		}
	}

	public sealed class TypeTreeNode : ILSpyTreeNode
	{
		readonly TypeDefinition type;
		readonly AssemblyTreeNode parentAssemblyNode;

		public TypeTreeNode(TypeDefinition type, AssemblyTreeNode parentAssemblyNode)
		{
			if (parentAssemblyNode == null)
				throw new ArgumentNullException("parentAssemblyNode");
			if (type == null)
				throw new ArgumentNullException("type");
			this.type = type;
			this.parentAssemblyNode = parentAssemblyNode;
		}

		public TypeDefinition TypeDefinition
		{
			get { return type; }
		}

		public AssemblyTreeNode ParentAssemblyNode
		{
			get { return parentAssemblyNode; }
		}

		public string Name
		{
			get { return type.Name; }
		}

		public string Namespace
		{
			get { return type.Namespace; }
		}

		public override bool IsPublicAPI
		{
			get
			{
				switch (type.Attributes & TypeAttributes.VisibilityMask)
				{
					case TypeAttributes.Public:
					case TypeAttributes.NestedPublic:
					case TypeAttributes.NestedFamily:
					case TypeAttributes.NestedFamORAssem:
						return true;
					default:
						return false;
				}
			}
		}

		protected override void LoadChildren()
		{
			if (type.BaseType != null || type.HasInterfaces)
				this.Children.Add(new BaseTypesTreeNode(type));
			if (!type.IsSealed)
				this.Children.Add(new DerivedTypesTreeNode(parentAssemblyNode.AssemblyList, type));
			foreach (TypeDefinition nestedType in type.NestedTypes.OrderBy(m => m.Name))
			{
				this.Children.Add(new TypeTreeNode(nestedType, parentAssemblyNode));
			}
			foreach (FieldDefinition field in type.Fields.OrderBy(m => m.Name))
			{
				this.Children.Add(new FieldTreeNode(field));
			}

			foreach (PropertyDefinition property in type.Properties.OrderBy(m => m.Name))
			{
				this.Children.Add(new PropertyTreeNode(property));
			}
			foreach (EventDefinition ev in type.Events.OrderBy(m => m.Name))
			{
				this.Children.Add(new EventTreeNode(ev));
			}
			HashSet<MethodDefinition> accessorMethods = type.GetAccessorMethods();
			foreach (MethodDefinition method in type.Methods.OrderBy(m => m.Name))
			{
				if (!accessorMethods.Contains(method))
				{
					this.Children.Add(new MethodTreeNode(method));
				}
			}
		}

		public override void Decompile(Language language, ITextOutput output, DecompilationOptions options)
		{
			language.DecompileType(type, output, options);
		}
	}

	sealed class BaseTypesTreeNode : ILSpyTreeNode
	{
		readonly TypeDefinition type;

		public BaseTypesTreeNode(TypeDefinition type)
		{
			this.type = type;
		}

		protected override void LoadChildren()
		{
			AddBaseTypes(Children, type);
		}

		internal static void AddBaseTypes(List<ILSpyTreeNode> children, TypeDefinition type)
		{
			if (type.BaseType != null)
				children.Add(new BaseTypesEntryNode(type.BaseType, false));
			foreach (TypeReference i in type.Interfaces)
			{
				children.Add(new BaseTypesEntryNode(i, true));
			}
		}

		public override void Decompile(Language language, ITextOutput output, DecompilationOptions options)
		{
			foreach (ILSpyTreeNode child in this.Children)
			{
				child.Decompile(language, output, options);
			}
		}
	}

	sealed class BaseTypesEntryNode : ILSpyTreeNode
	{
		private readonly TypeReference tr;
		private TypeDefinition def;
		private readonly bool isInterface;

		public BaseTypesEntryNode(TypeReference tr, bool isInterface)
		{
			if (tr == null)
				throw new ArgumentNullException("tr");
			this.tr = tr;
			this.def = tr.Resolve();
			this.isInterface = isInterface;
		}

		protected override void LoadChildren()
		{
			if (def != null)
				BaseTypesTreeNode.AddBaseTypes(this.Children, def);
		}

		public override void Decompile(Language language, ITextOutput output, DecompilationOptions options)
		{
			language.WriteCommentLine(output, language.TypeToString(tr, true));
		}
	}

	sealed class DerivedTypesTreeNode : ILSpyTreeNode
	{
		readonly AssemblyList list;
		readonly TypeDefinition type;

		public DerivedTypesTreeNode(AssemblyList list, TypeDefinition type)
		{
			this.list = list;
			this.type = type;
		}

		protected override void LoadChildren()
		{
			var assemblies = list.GetAssemblies().Select(node => node.ModuleDefinition).Where(asm => asm != null).ToArray();
			FindDerivedTypes(type, assemblies);
		}

		internal static IEnumerable<DerivedTypesEntryNode> FindDerivedTypes(TypeDefinition type, ModuleDefinition[] assemblies)
		{
			foreach (ModuleDefinition module in assemblies)
			{
				foreach (TypeDefinition td in TreeTraversal.PreOrder(module.Types, t => t.NestedTypes))
				{
					if (type.IsInterface && td.HasInterfaces)
					{
						foreach (TypeReference typeRef in td.Interfaces)
						{
							if (IsSameType(typeRef, type))
								yield return new DerivedTypesEntryNode(td, assemblies);
						}
					}
					else if (!type.IsInterface && td.BaseType != null && IsSameType(td.BaseType, type))
					{
						yield return new DerivedTypesEntryNode(td, assemblies);
					}
				}
			}
		}

		static bool IsSameType(TypeReference typeRef, TypeDefinition type)
		{
			if (typeRef.FullName == type.FullName)
				return true;
			if (typeRef.Name != type.Name || type.Namespace != typeRef.Namespace)
				return false;
			if (typeRef.IsNested || type.IsNested)
				if (!typeRef.IsNested || !type.IsNested || !IsSameType(typeRef.DeclaringType, type.DeclaringType))
					return false;
			var gTypeRef = typeRef as GenericInstanceType;
			if (gTypeRef != null || type.HasGenericParameters)
				if (gTypeRef == null || !type.HasGenericParameters || gTypeRef.GenericArguments.Count != type.GenericParameters.Count)
					return false;
			return true;
		}

		public override void Decompile(Language language, ITextOutput output, DecompilationOptions options)
		{
			foreach (ILSpyTreeNode child in Children)
			{
				child.Decompile(language, output, options);
			}
		}
	}

	class DerivedTypesEntryNode : ILSpyTreeNode
	{
		private readonly TypeDefinition type;
		private readonly ModuleDefinition[] assemblies;

		public DerivedTypesEntryNode(TypeDefinition type, ModuleDefinition[] assemblies)
		{
			this.type = type;
			this.assemblies = assemblies;
		}

		public override bool IsPublicAPI
		{
			get
			{
				switch (type.Attributes & TypeAttributes.VisibilityMask)
				{
					case TypeAttributes.Public:
					case TypeAttributes.NestedPublic:
					case TypeAttributes.NestedFamily:
					case TypeAttributes.NestedFamORAssem:
						return true;
					default:
						return false;
				}
			}
		}

		protected override void LoadChildren()
		{
			DerivedTypesTreeNode.FindDerivedTypes(type, assemblies);
		}

		public override void Decompile(Language language, ITextOutput output, DecompilationOptions options)
		{
			language.WriteCommentLine(output, language.TypeToString(type, true));
		}
	}

	public sealed class FieldTreeNode : ILSpyTreeNode
	{
		readonly FieldDefinition field;

		public FieldDefinition FieldDefinition
		{
			get { return field; }
		}

		public FieldTreeNode(FieldDefinition field)
		{
			if (field == null)
				throw new ArgumentNullException("field");
			this.field = field;
		}

		private static bool IsDecimalConstant(FieldDefinition field)
		{
			var fieldType = field.FieldType;
			if (fieldType.Name == "Decimal" && fieldType.Namespace == "System")
			{
				if (field.HasCustomAttributes)
				{
					var attrs = field.CustomAttributes;
					for (int i = 0; i < attrs.Count; i++)
					{
						var attrType = attrs[i].AttributeType;
						if (attrType.Name == "DecimalConstantAttribute" && attrType.Namespace == "System.Runtime.CompilerServices")
							return true;
					}
				}
			}
			return false;
		}

		public override void Decompile(Language language, ITextOutput output, DecompilationOptions options)
		{
			language.DecompileField(field, output, options);
		}

		public override bool IsPublicAPI
		{
			get
			{
				return field.IsPublic || field.IsFamily || field.IsFamilyOrAssembly;
			}
		}
	}

	/// <summary>
	/// Represents a property in the TreeView.
	/// </summary>
	public sealed class PropertyTreeNode : ILSpyTreeNode
	{
		readonly PropertyDefinition property;
		readonly bool isIndexer;

		public PropertyTreeNode(PropertyDefinition property)
		{
			if (property == null)
				throw new ArgumentNullException("property");
			this.property = property;
			// using (LoadedAssembly.DisableAssemblyLoad())
			{
				this.isIndexer = property.IsIndexer();
			}

			if (property.GetMethod != null)
				this.Children.Add(new MethodTreeNode(property.GetMethod));
			if (property.SetMethod != null)
				this.Children.Add(new MethodTreeNode(property.SetMethod));
			if (property.HasOtherMethods)
			{
				foreach (var m in property.OtherMethods)
					this.Children.Add(new MethodTreeNode(m));
			}

		}

		public PropertyDefinition PropertyDefinition
		{
			get { return property; }
		}

		private static MethodAttributes GetAttributesOfMostAccessibleMethod(PropertyDefinition property)
		{
			// There should always be at least one method from which to
			// obtain the result, but the compiler doesn't know this so
			// initialize the result with a default value
			MethodAttributes result = (MethodAttributes)0;

			// Method access is defined from inaccessible (lowest) to public (highest)
			// in numeric order, so we can do an integer comparison of the masked attribute
			int accessLevel = 0;

			if (property.GetMethod != null)
			{
				int methodAccessLevel = (int)(property.GetMethod.Attributes & MethodAttributes.MemberAccessMask);
				if (accessLevel < methodAccessLevel)
				{
					accessLevel = methodAccessLevel;
					result = property.GetMethod.Attributes;
				}
			}

			if (property.SetMethod != null)
			{
				int methodAccessLevel = (int)(property.SetMethod.Attributes & MethodAttributes.MemberAccessMask);
				if (accessLevel < methodAccessLevel)
				{
					accessLevel = methodAccessLevel;
					result = property.SetMethod.Attributes;
				}
			}

			if (property.HasOtherMethods)
			{
				foreach (var m in property.OtherMethods)
				{
					int methodAccessLevel = (int)(m.Attributes & MethodAttributes.MemberAccessMask);
					if (accessLevel < methodAccessLevel)
					{
						accessLevel = methodAccessLevel;
						result = m.Attributes;
					}
				}
			}

			return result;
		}

		public override void Decompile(Language language, ITextOutput output, DecompilationOptions options)
		{
			language.DecompileProperty(property, output, options);
		}

		public override bool IsPublicAPI
		{
			get
			{
				switch (GetAttributesOfMostAccessibleMethod(property) & MethodAttributes.MemberAccessMask)
				{
					case MethodAttributes.Public:
					case MethodAttributes.Family:
					case MethodAttributes.FamORAssem:
						return true;
					default:
						return false;
				}
			}
		}
	}

	public sealed class EventTreeNode : ILSpyTreeNode
	{
		readonly EventDefinition ev;

		public EventTreeNode(EventDefinition ev)
		{
			if (ev == null)
				throw new ArgumentNullException("ev");
			this.ev = ev;

			if (ev.AddMethod != null)
				this.Children.Add(new MethodTreeNode(ev.AddMethod));
			if (ev.RemoveMethod != null)
				this.Children.Add(new MethodTreeNode(ev.RemoveMethod));
			if (ev.InvokeMethod != null)
				this.Children.Add(new MethodTreeNode(ev.InvokeMethod));
			if (ev.HasOtherMethods)
			{
				foreach (var m in ev.OtherMethods)
					this.Children.Add(new MethodTreeNode(m));
			}
		}

		public EventDefinition EventDefinition
		{
			get { return ev; }
		}

		public static object GetText(EventDefinition eventDef, Language language)
		{
			return HighlightSearchMatch(eventDef.Name, " : " + language.TypeToString(eventDef.EventType, false, eventDef));
		}

		public override void Decompile(Language language, ITextOutput output, DecompilationOptions options)
		{
			language.DecompileEvent(ev, output, options);
		}


		public override bool IsPublicAPI
		{
			get
			{
				MethodDefinition accessor = ev.AddMethod ?? ev.RemoveMethod;
				return accessor != null && (accessor.IsPublic || accessor.IsFamilyOrAssembly || accessor.IsFamily);
			}
		}
	}

	/// <summary>
	/// Tree Node representing a field, method, property, or event.
	/// </summary>
	public sealed class MethodTreeNode : ILSpyTreeNode
	{
		readonly MethodDefinition method;

		public MethodDefinition MethodDefinition
		{
			get { return method; }
		}

		public MethodTreeNode(MethodDefinition method)
		{
			if (method == null)
				throw new ArgumentNullException("method");
			this.method = method;
		}

		public override bool IsPublicAPI
		{
			get
			{
				return method.IsPublic || method.IsFamily || method.IsFamilyOrAssembly;
			}
		}

		public override void Decompile(Language language, ITextOutput output, DecompilationOptions options)
		{
			language.DecompileMethod(method, output, options);
		}
	}
}
